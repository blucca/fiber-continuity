#!/usr/bin/env python3
"""Small in-memory checks for the fixed bounded-logit recentering operator."""
import json

import numpy as np

from bounded_logit_recenter import CONTROL_PARAMETERS, MODES, recenter


def fixture(y=21.5):
    points = np.column_stack((np.linspace(10.0, 54.0, 23), np.full(23, y), np.full(23, 20.0)))
    traces = {"coordinates": "ROI-local XYZ voxels", "shape_zyx": [40, 40, 64],
              "curves": [{"id": "predicted-17", "family": "V", "points_xyz": points.tolist(),
                          "gaps": [[3, 5]], "extra": {"preserve": True}},
                         {"id": 9, "family": "H", "points_xyz": points[[0, -1]].tolist(), "gaps": []}]}
    p = np.zeros((4, 40, 40, 64), np.float32)
    p[0] = 0.1
    p[1] = 0.8
    p[3] = 0.1
    return traces, p


def check_preserved(before, after):
    assert len(before["curves"]) == len(after["curves"]) == after["count"]
    for original, moved in zip(before["curves"], after["curves"]):
        for key in ("id", "family", "gaps"):
            assert moved[key] == original[key]
        assert len(moved["points_xyz"]) == len(original["points_xyz"])
        assert moved["source_curve_ids"] == [str(original["id"])]
        assert np.array_equal(np.asarray(moved["points_xyz"])[[0, -1]],
                              np.asarray(original["points_xyz"])[[0, -1]])
        assert np.isfinite(moved["points_xyz"]).all()
    assert after["curves"][0]["extra"] == before["curves"][0]["extra"]
    assert after["control_parameters"] == CONTROL_PARAMETERS
    assert after["topology_edits"] == 0 and after["labels_as_algorithm_input"] is False


def main():
    traces, p = fixture()
    flat = np.full((40, 40, 64), 100, np.uint8)
    for mode in MODES:
        output = recenter(traces, p, flat, mode)
        check_preserved(traces, output)
        for original, moved in zip(traces["curves"], output["curves"]):
            assert np.array_equal(original["points_xyz"], moved["points_xyz"])

    z, y, _ = np.indices(flat.shape)
    bright = (100 + 100 * np.exp(-((y - 20.0)**2 + (z - 20.0)**2) / 2.0)).astype(np.uint8)
    shifts = {}
    for mode in MODES:
        output = recenter(traces, p, bright, mode)
        check_preserved(traces, output)
        shift = np.asarray(output["curves"][0]["points_xyz"]) - np.asarray(traces["curves"][0]["points_xyz"])
        shifts[mode] = float(np.linalg.norm(shift, axis=1).max())
        assert shifts[mode] <= 1.5 + 1e-8
        assert np.array_equal(shift[:, 0], np.zeros(len(shift)))
        assert np.array_equal(output["curves"][1]["points_xyz"], traces["curves"][1]["points_xyz"])
        if mode == "ct-energy-control":
            assert np.allclose(shift[1:-1], [0.0, -1.5, 0.0], rtol=0, atol=1e-8)
        else:
            assert shifts[mode] == 0.0

    boundary_traces, boundary_p = fixture(y=3.0)
    boundary_ct = (100 + 100 * np.exp(-((y - 4.5)**2 + (z - 20.0)**2) / 2.0)).astype(np.uint8)
    boundary = recenter(boundary_traces, boundary_p, boundary_ct)
    for original, moved in zip(boundary_traces["curves"], boundary["curves"]):
        assert np.array_equal(original["points_xyz"], moved["points_xyz"])
    print(json.dumps({"status": "passed", "fixtures": ["flat identity both modes", "bright line bounded shift",
                                                      "whole-curve incomplete context identity"],
                      "max_shift_vox": shifts, "id_gaps_point_count_preserved": True,
                      "endpoint_pin": True, "control_parameters": CONTROL_PARAMETERS}, sort_keys=True))


if __name__ == "__main__":
    main()
