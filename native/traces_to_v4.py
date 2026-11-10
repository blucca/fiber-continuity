#!/usr/bin/env python3
"""Convert ROI-local XYZ trace envelopes to native V4 fibers at storage scale 1."""
import argparse
import json
import math
from pathlib import Path
import uuid


def xyz(values):
    result = [float(x) for x in values]
    if len(result) != 3 or not all(math.isfinite(x) for x in result):
        raise ValueError("expected three finite XYZ coordinates")
    return result


def convert(envelope, origin_xyz, volume_id, voxel_size_um=None):
    origin = xyz(origin_xyz)
    if not isinstance(volume_id, str) or not volume_id.strip():
        raise ValueError("provide metadata.json volume.id")
    spacing = xyz(voxel_size_um) if voxel_size_um is not None else None
    if spacing is not None and min(spacing) <= 0:
        raise ValueError("voxel sizes must be positive")
    metadata = {} if isinstance(envelope, list) else {
        k: v for k, v in envelope.items() if k != "curves"}
    if metadata.get("coordinates") not in (None, "local-xyz", "roi-local-xyz", "ROI-local XYZ voxels"):
        raise ValueError("expected a ROI-local XYZ trace envelope")
    curves = envelope if isinstance(envelope, list) else envelope["curves"]
    fibers, seen = [], set()
    for order, curve in enumerate(curves):
        source_id = curve["id"]
        key = json.dumps(source_id, sort_keys=True, allow_nan=False)
        if key in seen:
            raise ValueError("source curve IDs must be unique")
        seen.add(key)
        family = curve["family"]
        if family not in ("V", "H"):
            raise ValueError("family must be V or H")
        local = [xyz(point) for point in curve["points_xyz"]]
        if len(local) < 2:
            raise ValueError("each connected trace needs at least two points")
        points = [[x + shift for x, shift in zip(point, origin)] for point in local]
        if not all(math.isfinite(x) for point in points for x in point):
            raise ValueError("global XYZ must remain finite")
        annotations = {k: v for k, v in curve.items() if k != "points_xyz"}
        fiber = {
            "type": "vc3d_fiber", "version": 4, "uuid": str(uuid.uuid4()),
            "name": "curve:" + str(source_id), "optimization_mode": "lasagna",
            "coordinates": {"volume_uuid": volume_id, "scale_factor": 1},
            "hv_classification": {"manual_tag": family},
            "control_points": [{"position": points[0]}, {"position": points[-1]}],
            "control_point_ids": [0, 1], "line_points": points,
            "original_curve_id": source_id, "original_curve_order": order,
            "original_curve_annotations": annotations,
            "inferred_gap_point_ranges": curve.get("gaps", []),
            "source_envelope_metadata": metadata, "roi_origin_xyz": origin,
            "coordinate_units": "volume L0 voxel XYZ", "origin_applications": 1,
            "native_family_semantics": "program-selected family retained as fixed manual_tag",
        }
        if spacing is not None:
            fiber["voxel_size_um"] = spacing
        fibers.append(fiber)
    return fibers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--origin-xyz", type=float, nargs=3, required=True)
    parser.add_argument("--volume-id", required=True)
    parser.add_argument("--voxel-size-um", type=float, nargs=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fibers = convert(json.loads(args.traces.read_text()), args.origin_xyz,
                     args.volume_id, args.voxel_size_um)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(fibers, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"fiber_count": len(fibers),
                      "point_count": sum(len(f["line_points"]) for f in fibers),
                      "origin_applications": 1, "scale_factor": 1}))


if __name__ == "__main__":
    main()
