"""Whole-curve marginal geometric coverage; input points and joins stay intact.

Nearby same-family, aligned arcs share a selection budget. This is a ranking
proxy, with all input curves retained in the ranked archive. A consumer can
choose a curve count or a minimum marginal arc. No reference labels are read.
The small-ROI implementation targets <=500 curves; larger zones should index
and rank spatial blocks using the existing native catalog.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

STEP = 2.0
RADIUS = 1.5
COSINE = float(np.cos(np.deg2rad(15.0)))
TANGENT_SUPPORT = 8.0


def arc_length(points):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def _pieces(points):
    """Subdivide original segments; arc weights sum to the original length."""
    p = np.asarray(points, float)
    assert p.ndim == 2 and p.shape[1] == 3 and len(p) >= 2 and np.isfinite(p).all()
    arc = arc_length(p)
    assert arc[-1] > 0
    starts, deltas, weights, locations = [], [], [], []
    for i, (a, b) in enumerate(zip(p[:-1], p[1:])):
        length = arc[i+1]-arc[i]
        if length <= 1e-10:
            continue
        n = max(1, int(np.ceil(length/STEP)))
        t = np.arange(n)/n
        starts.append(a+t[:, None]*(b-a))
        deltas.append(np.repeat(((b-a)/n)[None], n, axis=0))
        weights.append(np.full(n, length/n))
        locations.append(arc[i]+(t+.5/n)*length)
    starts, deltas, weights, s = map(np.concatenate, (starts, deltas, weights, locations))
    def at(x):
        return np.stack([np.interp(x, arc, p[:, j]) for j in range(3)], axis=-1)
    tangent = at(np.minimum(arc[-1], s+TANGENT_SUPPORT/2))-at(np.maximum(0., s-TANGENT_SUPPORT/2))
    norm = np.linalg.norm(tangent, axis=1)
    # A local direction handles a nonlocal return in the ranking proxy only.
    tangent[norm <= 1e-10] = deltas[norm <= 1e-10]
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    assert np.isclose(weights.sum(), arc[-1]) and weights.max() <= STEP+1e-8
    return starts, deltas, weights, tangent


def rank_curves(curves):
    """Greedy unique-arc ranking with deterministic length / source / ID ties."""
    if not curves:
        return [], {'rows': [], 'sample_count': 0, 'aligned_neighbor_pairs': 0}
    assert len({str(c['id']) for c in curves}) == len(curves)
    arrays = [_pieces(c['points_xyz']) for c in curves]
    starts, deltas, weights, tangent = [np.concatenate([a[j] for a in arrays]) for j in range(4)]
    owner = np.repeat(np.arange(len(curves)), [len(a[2]) for a in arrays])
    family = np.array([c['family'] for c in curves])[owner]
    midpoint = starts+deltas*.5
    index = cKDTree(midpoint)
    queries, targets = [], []
    # Each target segment has length <=2; midpoint radius RADIUS+1 encloses
    # every possible exact projection within RADIUS of that segment.
    for low in range(0, len(midpoint), 512):
        nearby = index.query_ball_point(midpoint[low:low+512], RADIUS+STEP/2, workers=2)
        q = np.repeat(np.arange(low, low+len(nearby)), [len(a) for a in nearby])
        t = np.concatenate(nearby).astype(int)
        different = (owner[q] != owner[t]) & (family[q] == family[t])
        q, t = q[different], t[different]
        if not len(q):
            continue
        projection = np.sum((midpoint[q]-starts[t])*deltas[t], axis=1)/np.sum(deltas[t]*deltas[t], axis=1)
        projected = starts[t]+np.clip(projection, 0., 1.)[:, None]*deltas[t]
        distance = np.linalg.norm(midpoint[q]-projected, axis=1)
        cosine = np.abs(np.einsum('ij,ij->i', tangent[q], tangent[t]))
        valid = (distance <= RADIUS) & (cosine >= COSINE)
        queries.append(q[valid]); targets.append(owner[t[valid]])
    q = np.concatenate(queries) if queries else np.empty(0, int)
    t = np.concatenate(targets) if targets else np.empty(0, int)
    affected = [np.unique(q[t == i]) for i in range(len(curves))]
    total = np.bincount(owner, weights=weights, minlength=len(curves))
    covered = np.zeros(len(weights), bool)
    remaining = set(range(len(curves)))
    order, rows = [], []
    while remaining:
        gain = np.bincount(owner, weights=weights*~covered, minlength=len(curves))
        best = min(remaining, key=lambda i: (-float(gain[i]), -float(total[i]),
                   curves[i].get('source_kind', ''), str(curves[i]['id'])))
        order.append(best)
        rows.append({'rank': len(order), 'curve_id': curves[best]['id'],
                     'source_kind': curves[best].get('source_kind', ''),
                     'length_vox': float(total[best]), 'marginal_arc_vox': float(gain[best]),
                     'overlap_fraction_at_selection': float(1.-gain[best]/total[best])})
        covered[affected[best]] = True
        remaining.remove(best)
    # Whole-curve permutation only: no averaging, cuts, or cross-curve joins.
    return [curves[i] for i in order], {'rows': rows, 'sample_count': len(weights),
           'aligned_neighbor_pairs': len(q), 'parameters': {
               'radius_vox': RADIUS, 'max_angle_degrees': 15., 'tangent_support_vox': TANGENT_SUPPORT,
               'max_step_vox': STEP, 'ranking': 'greedy marginal aligned same-family geometric arc'}}
