#!/usr/bin/env python3
"""Read the native binary64 AFV SQLite schema emitted by AVF_SPLINE_GENERATOR.

The measured writer is Qualzz/AVF_SPLINE_GENERATOR@bee798f7. Blocks share one
endpoint; retain that point once. The caller supplies the evaluation ROI origin.
"""
import argparse
import json
from pathlib import Path
import sqlite3

import numpy as np


def read_afv(path, case, origin=(0, 0, 0)):
    curves = []
    with sqlite3.connect("file:" + str(Path(path).resolve()) + "?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA application_id").fetchone()[0] == 0x56434643
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        metadata = {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM metadata")}
        assert metadata["complete"] and metadata["root"]["coordinate_order"] == "XYZ"
        assert metadata["frame"]["vc_open_data_source_coordinate_scale_factor"] == 1
        for identifier, family, count, recorded_length in db.execute(
            "SELECT id,family,point_count,length FROM fibers ORDER BY id"
        ):
            arrays, previous = [], None
            for first, blob in db.execute(
                "SELECT first_segment,points FROM blocks WHERE fiber_id=? ORDER BY first_segment", (identifier,)
            ):
                points = np.frombuffer(blob, dtype="<f8").reshape(-1, 3)
                assert first == (0 if previous is None else previous[0] + len(previous[1]) - 1)
                if previous is not None:
                    assert np.array_equal(previous[1][-1], points[0])
                arrays.append(points if previous is None else points[1:])
                previous = (first, points)
            points = np.concatenate(arrays) - np.asarray(origin)
            length = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
            assert len(points) == count and np.isfinite(points).all() and family in ("V", "H")
            assert abs(length - recorded_length) < 1e-8
            curves.append({"id": f"afv/{identifier}", "family": family,
                           "points_xyz": points.tolist(), "gaps": [],
                           "source_curve_ids": [f"afv/{identifier}"]})
    return {"case": case, "coordinates": "ROI-local XYZ voxels", "origin_xyz": list(origin),
            "stage": "afv-import", "curves": curves, "count": len(curves),
            "length_voxels": sum(float(np.linalg.norm(np.diff(np.asarray(c["points_xyz"]), axis=0), axis=1).sum())
                                 for c in curves), "afv_metadata": metadata}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--afv", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--origin-xyz", nargs=3, type=float, default=(0, 0, 0))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = read_afv(args.afv, args.case, args.origin_xyz)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"case": args.case, "curves": result["count"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
