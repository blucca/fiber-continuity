#!/usr/bin/env python3
"""Apply the measured native cleanup to ROI-local XYZ trace envelopes.

Requires NumPy, SciPy and an existing ScrollPrize/villa checkout at
c3d9da6fe42c3bb46fd2603ca060845d843296c3. Fixed cleanup: 45 degrees,
minimum length 100 voxels, ExteriorBlack distance 16 voxels, local origin 0.
The pinned cut/thin source uses the measured SciPy hole-fill/cube-morphology
backend. Output feeds native/traces_to_v4.py with the ROI origin applied there.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from _cleanup_primitives import install

SOURCE_PIN = "c3d9da6fe42c3bb46fd2603ca060845d843296c3"
CLEANUP_SHA256 = "5216159a9b81d03867710c51fdc29c0a8ecd7e93f43d6fb7daaeec466fed1024"


def clean_envelope(envelope, ct, vesuvius_src):
    if ct.ndim != 3 or ct.dtype != np.uint8:
        raise ValueError("CT must be uint8 ZYX")
    if envelope.get("coordinates") not in (
            None, "local-xyz", "roi-local-xyz", "ROI-local XYZ voxels"):
        raise ValueError("expected ROI-local XYZ voxels")
    if "shape_zyx" in envelope and list(ct.shape) != envelope["shape_zyx"]:
        raise ValueError("CT shape must match the trace envelope")
    source = Path(vesuvius_src) / "vesuvius/fiber_spline_generator/cleanup.py"
    if hashlib.sha256(source.read_bytes()).hexdigest() != CLEANUP_SHA256:
        raise ValueError("cleanup.py must match the documented native source pin")
    # Load the single pinned file; its dependencies are NumPy and these two
    # process-local SciPy primitives used by ExteriorBlack.near.
    install()
    spec = importlib.util.spec_from_file_location("pinned_vesuvius_cleanup", source)
    cleanup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cleanup)
    black = cleanup.ExteriorBlack([0, 0, 0], list(ct.shape[::-1]))
    black.add(ct, [0, 0, 0])
    native = [{"family": ("V", "H").index(c["family"]),
               "points": np.asarray(c["points_xyz"]),
               "gaps": c.get("gaps", []),
               "source_curve_ids": c.get("source_curve_ids", [str(c["id"])])}
              for c in envelope["curves"]]
    cleaned = cleanup.clean(native, 45., 100., black, 16.)
    curves = [{"id": i, "family": ("V", "H")[c["family"]],
               "points_xyz": c["points"].tolist(), "gaps": c["gaps"],
               "source_curve_ids": c["source_curve_ids"]}
              for i, c in enumerate(cleaned)]
    result = dict(envelope, stage=envelope["stage"] + "-native-clean",
                  curves=curves, count=len(curves),
                  length_voxels=sum(float(np.linalg.norm(
                      np.diff(np.asarray(c["points_xyz"]), axis=0), axis=1).sum())
                      for c in curves))
    summary = {"input_curve_count": len(native), "curve_count": len(curves),
               "point_count": sum(len(c["points_xyz"]) for c in curves),
               "length_voxels": result["length_voxels"],
               "exterior_black_all_zero_cells": int(black.all_zero.sum()),
               "exterior_black_any_zero_cells": int(black.any_zero.sum()),
               "native_source_pin": SOURCE_PIN, "cleanup_source_sha256": CLEANUP_SHA256,
               "primitive_backend": "SciPy default 6-connected hole fill; radius-one cube morphology, border0",
               "max_join_angle_degrees": 45., "min_length_voxels": 100.,
               "black_distance_voxels": 16., "ct_local_origin_xyz": [0, 0, 0]}
    return result, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vesuvius-src", type=Path, required=True,
                        help="existing pinned checkout's vesuvius/src directory")
    parser.add_argument("--ct", type=Path, required=True, help="uint8 ZYX .npy CT block")
    parser.add_argument("--traces", type=Path, required=True, help="ROI-local XYZ raw envelope")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result, summary = clean_envelope(json.loads(args.traces.read_text()),
                                     np.load(args.ct, allow_pickle=False), args.vesuvius_src)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(summary, allow_nan=False))


if __name__ == "__main__":
    main()
