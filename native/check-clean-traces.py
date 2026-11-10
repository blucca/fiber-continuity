#!/usr/bin/env python3
"""One entirely synthetic fixture for the fixed measured cleanup contract."""
import argparse
import json
from pathlib import Path

import numpy as np
from clean_traces import clean_envelope

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--vesuvius-src", type=Path, required=True)
args = parser.parse_args()
ct = np.ones((128, 128, 128), dtype=np.uint8)
ct[:, :, :4] = 0  # A real exterior-black surface, including a 16-voxel hit.
curves = [
    {"id": "kept-V", "family": "V", "source_curve_ids": ["native-1", "native-2"],
     "gaps": [[30, 34]], "points_xyz": [[32, y, 66] for y in range(12, 125)]},
    {"id": 42, "family": "H", "points_xyz": [[64, 66, z] for z in range(6, 119)]},
    {"id": "black-near", "family": "H", "points_xyz": [[18, y, 66] for y in range(6, 119)]},
    {"id": "short", "family": "V", "points_xyz": [[64, 64, 20], [64, 64, 40]]},
    {"id": "sharp-gap", "family": "V", "gaps": [[60, 61]],
     "points_xyz": ([[64, y, 40] for y in range(40, 101)] +
                    [[64, 100, z] for z in range(41, 102)])},
]
envelope = {"format": "fiber-continuity-research-lines", "version": 1,
            "case": "entirely-synthetic", "coordinates": "ROI-local XYZ voxels",
            "shape_zyx": list(ct.shape), "stage": "synthetic-raw", "count": len(curves),
            "length_voxels": 0., "curves": curves, "provenance": {"synthetic": True}}
result, summary = clean_envelope(envelope, ct, args.vesuvius_src)
assert result["curves"] == [
    {"id": 0, "family": "V", "points_xyz": [[32., 12., 66.], [32., 42., 66.],
                                                   [32., 46., 66.], [32., 124., 66.]],
     "gaps": [[1, 2]], "source_curve_ids": ["native-1", "native-2"]},
    {"id": 1, "family": "H", "points_xyz": [[64., 66., 6.], [64., 66., 118.]],
     "gaps": [], "source_curve_ids": ["42"]},
]
assert result["stage"] == "synthetic-raw-native-clean"
assert result["count"] == 2 and result["length_voxels"] == 224.
assert {k: v for k, v in result.items() if k not in ("stage", "count", "length_voxels", "curves")} == {
    k: v for k, v in envelope.items() if k not in ("stage", "count", "length_voxels", "curves")}
assert summary["exterior_black_all_zero_cells"] == 1024
assert summary["ct_local_origin_xyz"] == [0, 0, 0]
print(json.dumps({"status": "passed", "fixture": "entirely synthetic",
                  "checks": ["45-degree sharp-gap cut", "100-voxel minimum length",
                             "16-voxel exterior-black rejection", "gap pins and remapping",
                             "V/H native mapping", "source IDs and fallback",
                             "envelope metadata and local origin0"],
                  "input_curve_count": 5, "curve_count": 2, "point_count": 6}, allow_nan=False))
