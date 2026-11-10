#!/usr/bin/env python3
"""Small entirely synthetic check of the trace → native V4 contract."""
import uuid
from traces_to_v4 import convert

curves = [
    {"id": "synthetic-V", "family": "V", "gaps": [[1, 2]],
     "points_xyz": [[0, 1, 2], [1, 1, 2], [2, 2, 2]]},
    {"id": 42, "family": "H", "points_xyz": [[2, 3, 4], [5, 3, 4]]},
]
fibers = convert({"curves": curves, "coordinates": "ROI-local XYZ voxels", "stage": "synthetic"},
                 [100, 200, 300], "synthetic-volume", [7.91] * 3)
assert len(fibers) == 2 and fibers[0]["line_points"] == [[100, 201, 302], [101, 201, 302], [102, 202, 302]]
assert fibers[0]["control_points"] == [{"position": [100, 201, 302]}, {"position": [102, 202, 302]}]
assert fibers[0]["inferred_gap_point_ranges"] == [[1, 2]]
assert fibers[1]["original_curve_id"] == 42 and fibers[1]["original_curve_order"] == 1
assert fibers[0]["original_curve_annotations"] == {k: v for k, v in curves[0].items() if k != "points_xyz"}
assert all(f["coordinates"] == {"volume_uuid": "synthetic-volume", "scale_factor": 1} for f in fibers)
assert all(uuid.UUID(f["uuid"]).version == 4 for f in fibers)
for bad in ([curves[0], curves[0]], {"curves": curves, "coordinates": "global-xyz"}):
    try:
        convert(bad, [100, 200, 300], "synthetic-volume")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate identity / global frame must stop conversion")
print("passed: synthetic XYZ origin once, identity/order/family/gaps/controls, duplicate/global-frame gates")
