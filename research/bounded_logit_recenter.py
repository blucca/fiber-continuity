#!/usr/bin/env python3
"""Fixed-scale bounded-logit recentering of predicted polylines.

Inputs are uint8 CT (ZYX), float32 probabilities (4,Z,Y,X; channels ordered
background/V/H/intersection), and an extended prediction JSON envelope with
ROI-local XYZ voxel coordinates. Only these three supplied inputs are opened.
Returns raw geometry for the upstream pinned native-cleanup stage.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from transverse_centering import center_scores, choose_center
from logit_maps import bounded_maps


@dataclass(frozen=True)
class Parameters:
    radius_vox: float = 1.5
    smoothing_sigma_vox: float = 2.0
    smoothing_step_vox: float = 0.5
    endpoint_pin: bool = True


PARAMETERS = Parameters()
MODES = ("ct-energy-control", "probability-only")
CONTROL_PARAMETERS = {
    "radius_vox": 1.5, "incoming_vox": 8.0, "smoothing_arc_sigma_vox": 2.0,
    "gate": 0.5, "shift_prior": "r2/8 both modes",
    "probability_energy": "logit clip1e-5 (sole new mechanism)",
    "ct_score": "CT_G1-transverse_G2, local_MAD",
    "ct_fine_sigma_vox": 1.0, "ct_fine_truncate": 4.0,
    "context_radius_vox": 8.0, "transverse_grid_step_vox": 0.5,
    "ct_background_sigma_vox": 2.0, "ct_background_truncate": 2.0,
    "ct_mad_radius_vox": 6.0, "ct_mad_scale": 1.4826,
    "ct_mad_floor_gray": 1.0, "smoothing_grid_max_step_vox": 0.5,
    "smoothing_truncate": 4.0, "sampling_order": 1, "sampling_mode": "nearest",
    "candidate_context_rule": "complete 33x33 context in [0,size-1]; otherwise zero selected shift",
    "endpoint_pin": True,
}


def arclength(points):
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def at_arc(points, arc, locations):
    return np.stack([np.interp(locations, arc, points[:, k]) for k in range(3)], axis=-1)


def incoming_tangents(points, arc, support):
    """Preceding original-arc direction, with forward fallback at the start."""
    directions = points - at_arc(points, arc, np.maximum(0.0, arc - support))
    lengths = np.linalg.norm(directions, axis=1)
    fallback = lengths < 1e-10
    directions[fallback] = (at_arc(points, arc, np.minimum(arc[-1], arc + support)) - points)[fallback]
    lengths = np.linalg.norm(directions, axis=1)
    if np.any(lengths < 1e-10):
        raise ValueError("predicted curve has a zero-geometry tangent")
    return directions / lengths[:, None]


def frames(tangents):
    anchor = np.eye(3)[np.argmin(np.abs(tangents), axis=1)]
    u = np.cross(tangents, anchor)
    u /= np.linalg.norm(u, axis=1)[:, None]
    v = np.cross(tangents, u)
    return u, v


def sample(field, xyz):
    coords = np.asarray(xyz[..., ::-1], np.float32).reshape(-1, 3).T
    return ndi.map_coordinates(field, coords, order=1, mode="nearest",
                               prefilter=False).reshape(xyz.shape[:-1])


def smooth_displacements(displacements, points, arc, tangents, size_xyz, parameters=PARAMETERS):
    """Original-arc Gaussian, transverse projection, bounded clipping, endpoint pin.

    Context gating precedes smoothing, so neighboring shifts can contribute
    through the Gaussian. Domain clipping scales along the transverse vector.
    Original knots and gap indices are retained.
    """
    regular = np.linspace(0.0, arc[-1], max(1, int(np.ceil(arc[-1] / parameters.smoothing_step_vox))) + 1)
    regular_step = regular[1] - regular[0]
    values = at_arc(displacements, arc, regular)
    values = ndi.gaussian_filter1d(values, parameters.smoothing_sigma_vox / regular_step,
                                  axis=0, mode="nearest")
    smooth = at_arc(values, regular, arc)
    smooth -= np.einsum("ij,ij->i", smooth, tangents)[:, None] * tangents
    length = np.linalg.norm(smooth, axis=1)
    smooth *= np.minimum(1.0, parameters.radius_vox / np.maximum(length, 1e-12))[:, None]
    upper = size_xyz - 1.0
    factors = np.ones_like(smooth)
    positive, negative = smooth > 1e-12, smooth < -1e-12
    np.divide(upper[None, :] - points, smooth, out=factors, where=positive)
    np.divide(-points, smooth, out=factors, where=negative)
    smooth *= np.clip(factors.min(axis=1), 0.0, 1.0)[:, None]
    unpinned = smooth.copy()
    if parameters.endpoint_pin:
        smooth[[0, -1]] = 0.0
    return smooth, unpinned


def validate_traces(traces, shape_zyx):
    if traces.get("coordinates", "ROI-local XYZ voxels") != "ROI-local XYZ voxels":
        raise ValueError("traces require ROI-local XYZ voxel coordinates")
    if list(traces.get("shape_zyx", shape_zyx)) != list(shape_zyx):
        raise ValueError("trace shape differs from CT shape")
    curves = traces["curves"]
    ids = [str(curve["id"]) for curve in curves]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate predicted curve id")
    size_xyz = np.asarray(shape_zyx[::-1], float)
    for curve in curves:
        points = np.asarray(curve["points_xyz"], float)
        if curve["family"] not in ("V", "H") or points.ndim != 2 or points.shape[1] != 3 or len(points) < 2:
            raise ValueError("curve requires family V/H and at least two XYZ points")
        if not np.isfinite(points).all() or not ((points >= 0.0) & (points <= size_xyz - 1.0)).all():
            raise ValueError("predicted points outside finite volume lattice")
        if arclength(points)[-1] <= 1e-10:
            raise ValueError("zero-geometry predicted curve")
        for low, high in curve.get("gaps", []):
            if not (0 <= low <= high < len(points)):
                raise ValueError("gap point-index range failed")


def recenter(traces, probabilities, ct, mode="ct-energy-control"):
    """Return one raw extended envelope; IDs, gaps and point counts are retained."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if ct.ndim != 3 or ct.dtype != np.uint8 or probabilities.dtype != np.float32 or probabilities.shape != (4,) + ct.shape:
        raise ValueError("input contract: CT uint8 ZYX, probabilities float32 shape (4,Z,Y,X)")
    validate_traces(traces, ct.shape)
    ct1 = ndi.gaussian_filter(ct.astype(np.float32), 1.0, mode="nearest", truncate=4.0)
    axis = np.arange(-8.0, 8.01, 0.5)
    uu, vv = np.meshgrid(axis, axis, indexing="ij")
    rr2 = uu * uu + vv * vv
    size_xyz = np.asarray(ct.shape[::-1], float)
    curves = []
    for curve in traces["curves"]:
        points = np.asarray(curve["points_xyz"], float)
        arc = arclength(points)
        tangent = incoming_tangents(points, arc, 8.0)
        u, v = frames(tangent)
        selected = np.zeros_like(points)
        for low in range(0, len(points), 96):
            high = min(low + 96, len(points))
            centres = points[low:high]
            xyz = (centres[:, None, None] + u[low:high, None, None] * uu[None, ..., None]
                   + v[low:high, None, None] * vv[None, ..., None])
            complete = ((xyz >= 0.0) & (xyz <= size_xyz - 1.0)).all((1, 2, 3))
            ct_patch = sample(ct1, xyz)
            fp = sample(probabilities[1 if curve["family"] == "V" else 2], xyz) + sample(probabilities[3], xyz)
            _, evidence = center_scores(ct_patch, fp)
            values = bounded_maps(fp, evidence["dog_z"], rr2)[mode]
            uv, available = choose_center(values, radius_vox=1.5)
            uv[~(complete & available)] = 0.0
            selected[low:high] = u[low:high] * uv[:, :1] + v[low:high] * uv[:, 1:]
        shift, _ = smooth_displacements(selected, points, arc, tangent, size_xyz)
        moved = points + shift
        assert np.isfinite(moved).all() and ((moved >= 0.0) & (moved <= size_xyz - 1.0)).all()
        assert np.linalg.norm(shift, axis=1).max() <= 1.5 + 1e-8
        assert np.max(np.abs(np.einsum("ij,ij->i", shift, tangent))) < 1e-8
        assert np.array_equal(moved[[0, -1]], points[[0, -1]])
        curves.append(dict(curve, points_xyz=moved.tolist(), source_curve_ids=[str(curve["id"])]))
    metadata = {key: value for key, value in traces.items() if key not in ("curves", "count", "length_voxels")}
    return dict(metadata, stage="fixed-recenter-" + mode, curves=curves, count=len(curves),
                length_voxels=sum(float(arclength(np.asarray(curve["points_xyz"]))[-1]) for curve in curves),
                control_parameters=dict(CONTROL_PARAMETERS), labels_as_algorithm_input=False, topology_edits=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ct", required=True, type=Path)
    parser.add_argument("--probabilities", required=True, type=Path)
    parser.add_argument("--traces", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=MODES, default="ct-energy-control")
    args = parser.parse_args()
    ct = np.load(args.ct, allow_pickle=False)
    probabilities = np.load(args.probabilities, mmap_mode="r", allow_pickle=False)
    traces = json.loads(args.traces.read_text())
    result = recenter(traces, probabilities, ct, args.mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"stage": result["stage"], "count": result["count"], "length_voxels": result["length_voxels"]}))


if __name__ == "__main__":
    main()
