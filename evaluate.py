#!/usr/bin/env python3
"""Manual-NML arc coverage, observed tree-ID switches, and chain continuity.

Geometry is local XYZ in the original 7.91 um ROI frame. Arrays are ZYX.
Only NumPy is required. See contract.md for the declared observable scope.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np

EPS = 1e-8


@dataclass(frozen=True)
class Parameters:
    radius_vox: float = 2.0
    ambiguity_margin_vox: float = 1.0
    min_support_vox: float = 8.0
    max_step_vox: float = 1.0
    boundary_band_vox: float = 2.0

    def __post_init__(self):
        values = asdict(self)
        assert all(math.isfinite(v) for v in values.values()), values
        assert self.radius_vox > 0 and self.min_support_vox > 0
        assert self.ambiguity_margin_vox >= 0 and self.boundary_band_vox >= 0
        assert 0 < self.max_step_vox <= 1.0


def inside_roi(point, size_xyz):
    p = np.asarray(point)
    return bool(np.all(p >= 0) and np.all(p < size_xyz))


def boundary_distance(point, size_xyz):
    return float(np.min(np.minimum(point, size_xyz - point)))


def clip_parameters(a, b, size_xyz):
    """Line/AABB clip; the exclusive high face has zero arc measure."""
    lo, hi = 0.0, 1.0
    for k in range(3):
        delta = b[k] - a[k]
        if abs(delta) < EPS:
            if a[k] < 0 or a[k] > size_xyz[k]:
                return None
        else:
            t0, t1 = -a[k] / delta, (size_xyz[k] - a[k]) / delta
            lo, hi = max(lo, min(t0, t1)), min(hi, max(t0, t1))
            if hi <= lo:
                return None
    if hi <= lo or not inside_roi(a + (lo + hi) * 0.5 * (b - a), size_xyz):
        return None
    return lo, hi


def sample_piece(a, b, arc0, t0, t1, max_step):
    length = float(np.linalg.norm(b - a))
    piece_length = length * (t1 - t0)
    if piece_length <= EPS:
        return
    n = max(1, int(math.ceil(piece_length / max_step)))
    ts = np.linspace(t0, t1, n + 1)
    points = a[None, :] + ts[:, None] * (b - a)[None, :]
    for i in range(n):
        yield points[i], points[i + 1], arc0 + ts[i] * length, arc0 + ts[i + 1] * length


def maximal_nonbranch_paths(adjacency):
    """Partition original undirected edges once; degree-3 and tree IDs stay intact."""
    used, paths = set(), []

    def key(u, v):
        return (min(u, v), max(u, v))

    def walk(start, nxt):
        nodes = [start, nxt]
        used.add(key(start, nxt))
        prev, cur = start, nxt
        while len(adjacency[cur]) == 2:
            candidates = [v for v in sorted(adjacency[cur]) if v != prev]
            v = candidates[0]
            if key(cur, v) in used:
                break
            used.add(key(cur, v))
            nodes.append(v)
            prev, cur = cur, v
        paths.append(nodes)

    for u in sorted(adjacency):
        if len(adjacency[u]) != 2:
            for v in sorted(adjacency[u]):
                if key(u, v) not in used:
                    walk(u, v)
    for u in sorted(adjacency):
        for v in sorted(adjacency[u]):
            if key(u, v) not in used:
                walk(u, v)
    assert len(used) == sum(map(len, adjacency.values())) // 2
    return paths


@dataclass
class PreparedReference:
    origin_xyz: np.ndarray
    size_xyz: np.ndarray
    segments: np.ndarray
    tree_codes: np.ndarray
    path_codes: np.ndarray
    original_edges: list
    arc_starts: np.ndarray
    arc_ends: np.ndarray
    fully_inside: np.ndarray
    boundary_band: np.ndarray
    paths: list
    trees: list
    summary: dict


def prepare_reference(reference, parameters=Parameters(), case=None):
    assert reference['format'] == 'WebKnossos NML'
    origin_xyz = np.asarray(reference['filename_origin_zyx'][::-1], dtype=np.float64)
    size_xyz = np.full(3, float(reference['roi_size']), dtype=np.float64)
    assert origin_xyz.shape == (3,) and np.all(size_xyz > 0)
    parts, tree_codes, path_codes, original_edges = [], [], [], []
    starts, ends, fully_inside, band = [], [], [], []
    paths, trees, all_degrees = [], [], Counter()
    original_length = 0.0
    original_edge_count = zero_length_count = clipped_edge_count = outside_edge_count = 0
    original_inside_nodes = original_inside_edges = 0
    all_tree_ids = set()
    for tree in reference['trees']:
        tree_id = str(tree['attributes']['id'])
        assert tree_id not in all_tree_ids
        all_tree_ids.add(tree_id)
        tree_code = len(trees)
        nodes, adjacency = {}, {}
        for node in tree['nodes']:
            nid = int(node['id'])
            assert nid not in nodes
            xyz = np.asarray(node['xyz_local'], dtype=np.float64)
            assert xyz.shape == (3,) and np.all(np.isfinite(xyz))
            assert np.allclose(np.asarray(node['xyz'], dtype=float), xyz + origin_xyz, atol=1e-6, rtol=0)
            assert bool(node['inside_roi']) == inside_roi(xyz, size_xyz)
            nodes[nid], adjacency[nid] = xyz, set()
            original_inside_nodes += bool(node['inside_roi'])
        edge_map = {}
        for edge in tree['edges']:
            u, v = int(edge['source']), int(edge['target'])
            assert u in nodes and v in nodes and u != v
            key = (min(u, v), max(u, v))
            assert key not in edge_map
            edge_map[key] = edge
            adjacency[u].add(v)
            adjacency[v].add(u)
            expected_inside = inside_roi(nodes[u], size_xyz) and inside_roi(nodes[v], size_xyz)
            assert bool(edge['inside_roi']) == expected_inside
            original_inside_edges += expected_inside
        degrees = {nid: len(adj) for nid, adj in adjacency.items()}
        all_degrees.update(degrees.values())
        max_degree = max(degrees.values(), default=0)
        assert max_degree == tree['max_degree']
        unseen, components = set(nodes), []
        while unseen:
            stack = [unseen.pop()]
            count = 0
            while stack:
                u = stack.pop()
                count += 1
                for v in adjacency[u]:
                    if v in unseen:
                        unseen.remove(v)
                        stack.append(v)
            components.append(count)
        assert sorted(components) == sorted(tree['connected_component_node_counts'])
        path_nodes = maximal_nonbranch_paths(adjacency)
        assert sum(len(p) - 1 for p in path_nodes) == len(edge_map)
        tree_summary = {
            'tree_id': tree_id, 'attributes': dict(tree['attributes']),
            'node_count': len(nodes), 'edge_count': len(edge_map),
            'connected_component_node_counts': components, 'max_degree': max_degree,
            'branch_node_ids': sorted(n for n, d in degrees.items() if d >= 3),
            'isolated_node_ids': sorted(n for n, d in degrees.items() if d == 0),
            'path_ids': [],
        }
        for path_number, node_ids in enumerate(path_nodes):
            path_code = len(paths)
            path_id = f'{tree_id}:p{path_number:03d}'
            tree_summary['path_ids'].append(path_id)
            indices, arc0, zero_count, inside_edge_length = [], 0.0, 0, 0.0
            for u, v in zip(node_ids, node_ids[1:]):
                a, b = nodes[u], nodes[v]
                edge = edge_map[(min(u, v), max(u, v))]
                length = float(np.linalg.norm(b - a))
                original_edge_count += 1
                original_length += length
                if length <= EPS:
                    zero_length_count += 1
                    zero_count += 1
                else:
                    clipped = clip_parameters(a, b, size_xyz)
                    if clipped is None:
                        outside_edge_count += 1
                    else:
                        t0, t1 = clipped
                        clipped_edge_count += 1
                        inside_edge_length += length * (t1 - t0)
                        for sa, sb, ss, se in sample_piece(a, b, arc0, t0, t1, parameters.max_step_vox):
                            indices.append(len(parts))
                            parts.append([sa, sb])
                            tree_codes.append(tree_code)
                            path_codes.append(path_code)
                            original_edges.append([u, v])
                            starts.append(ss)
                            ends.append(se)
                            fully_inside.append(bool(edge['inside_roi']))
                            band.append(boundary_distance((sa + sb) * 0.5, size_xyz) <= parameters.boundary_band_vox)
                arc0 += length
            visible_components = []
            for i in indices:
                if not visible_components or abs(starts[i] - visible_components[-1][1]) > EPS:
                    visible_components.append([float(starts[i]), float(ends[i])])
                else:
                    visible_components[-1][1] = float(ends[i])
            longest_visible = max((stop - start for start, stop in visible_components), default=0.0)
            paths.append({
                'path_id': path_id, 'tree_id': tree_id, 'tree_code': tree_code,
                'node_ids': node_ids, 'endpoint_degrees': [degrees[node_ids[0]], degrees[node_ids[-1]]],
                'edge_count': len(node_ids) - 1, 'zero_length_edge_count': zero_count,
                'original_length_vox': arc0, 'inside_length_vox': inside_edge_length,
                'outside_length_vox': max(0.0, arc0 - inside_edge_length), 'sample_indices': indices,
                'visible_component_count': len(visible_components),
                'longest_visible_component_vox': longest_visible,
                'visible_arc_components': [{'arc_start_vox': start, 'arc_end_vox': stop,
                                            'length_vox': stop - start} for start, stop in visible_components],
                'points_xyz': [nodes[n].tolist() for n in node_ids],
            })
        trees.append(tree_summary)
    assert len(trees) == reference['tree_count']
    assert sum(t['node_count'] for t in trees) == reference['node_count']
    assert original_edge_count == reference['edge_count']
    assert original_inside_nodes == reference['inside_node_count']
    assert original_inside_edges == reference['inside_edge_count']
    segments = np.asarray(parts, dtype=np.float64).reshape(-1, 2, 3)
    arc_starts, arc_ends = np.asarray(starts), np.asarray(ends)
    weights = arc_ends - arc_starts
    f_inside, b_band = np.asarray(fully_inside, bool), np.asarray(band, bool)
    visible_ceiling = sum(p['longest_visible_component_vox'] for p in paths)
    summary = {
        'case': case, 'format': reference['format'], 'parameters': reference['parameters'],
        'geometry_axes': 'xyz', 'array_axes': 'zyx', 'coordinates': 'local-xyz',
        'origin_xyz': origin_xyz.tolist(), 'origin_zyx': origin_xyz[::-1].tolist(),
        'roi_shape_zyx': size_xyz[::-1].astype(int).tolist(),
        'roi_bounds_local_xyz': {'low_inclusive': [0, 0, 0], 'high_exclusive': size_xyz.tolist()},
        'tree_count': len(trees), 'node_count': reference['node_count'],
        'original_edge_count': original_edge_count, 'original_inside_node_count': original_inside_nodes,
        'original_fully_inside_edge_count': original_inside_edges,
        'degree_histogram': dict(sorted(all_degrees.items())),
        'degree3_node_count': all_degrees[3], 'zero_length_edge_count': zero_length_count,
        'maximal_nonbranch_path_count': len(paths),
        'inside_maximal_path_count': int(sum(p['inside_length_vox'] > EPS for p in paths)),
        'visible_component_count': sum(p['visible_component_count'] for p in paths),
        'sum_path_longest_visible_component_vox': visible_ceiling,
        'same_chain_continuity_ceiling': visible_ceiling / float(weights.sum()) if weights.sum() > EPS else None,
        'positive_length_edges_intersecting_roi': clipped_edge_count,
        'positive_length_edges_wholly_outside_roi': outside_edge_count,
        'original_manual_arc_vox': original_length, 'inside_manual_arc_vox': float(weights.sum()),
        'outside_manual_arc_vox': max(0.0, original_length - float(weights.sum())),
        'fully_inside_original_edge_arc_vox': float(weights[f_inside].sum()),
        'boundary_intersecting_original_edge_arc_vox': float(weights[~f_inside].sum()),
        'roi_boundary_band_arc_vox': float(weights[b_band].sum()),
        'sample_segment_count': len(segments),
        'max_sample_segment_length_vox': float(weights.max()) if len(weights) else 0.0,
        'manual_tree_names_scope': 'annotator names; geometric matching uses all original tree IDs',
        'trees': trees,
        'paths': [{k: v for k, v in p.items() if k not in {'tree_code', 'sample_indices', 'points_xyz'}} for p in paths],
    }
    return PreparedReference(origin_xyz, size_xyz, segments, np.asarray(tree_codes, int),
                             np.asarray(path_codes, int), original_edges, arc_starts, arc_ends,
                             f_inside, b_band, paths, trees, summary)


class SegmentIndex:
    """Small exact point-to-segment queries, spatial hash of <=1 voxel segments."""
    def __init__(self, segments, labels, radius):
        self.segments = np.asarray(segments, dtype=np.float64).reshape(-1, 2, 3)
        self.labels = np.asarray(labels, dtype=int)
        self.radius = float(radius)
        self.cell = max(4.0, self.radius + 0.5)
        self.a = self.segments[:, 0]
        self.v = self.segments[:, 1] - self.a
        self.v2 = np.einsum('ij,ij->i', self.v, self.v)
        assert np.all(self.v2 <= 1.0 + EPS) and np.all(self.v2 > 0)
        grid = defaultdict(list)
        cells = np.floor(self.segments.mean(1) / self.cell).astype(int)
        for i, key in enumerate(cells):
            grid[tuple(key)].append(i)
        self.grid = {k: np.asarray(v, dtype=int) for k, v in grid.items()}
        reach = int(math.ceil((self.radius + 0.5) / self.cell))
        self.offsets = list(itertools.product(range(-reach, reach + 1), repeat=3))
        self.cache = {}

    def nearby(self, point):
        cell = tuple(np.floor(np.asarray(point) / self.cell).astype(int))
        if cell not in self.cache:
            arrays = [self.grid.get(tuple(cell[k] + d[k] for k in range(3))) for d in self.offsets]
            arrays = [a for a in arrays if a is not None]
            self.cache[cell] = np.concatenate(arrays) if arrays else np.empty(0, dtype=int)
        ids = self.cache[cell]
        if not len(ids):
            return ids, np.empty(0, dtype=float)
        aq = np.asarray(point)[None, :] - self.a[ids]
        t = np.clip(np.einsum('ij,ij->i', aq, self.v[ids]) / self.v2[ids], 0, 1)
        residual = aq - t[:, None] * self.v[ids]
        d2 = np.einsum('ij,ij->i', residual, residual)
        keep = d2 <= self.radius ** 2 + EPS
        return ids[keep], np.sqrt(d2[keep])


def load_predictions(path):
    path = Path(path)
    if path.suffix == '.npz':
        with np.load(path, allow_pickle=False) as d:
            points = np.asarray(d['points_xyz'], dtype=float)
            offsets = np.asarray(d['offsets'], dtype=np.int64)
            assert points.ndim == 2 and points.shape[1] == 3
            assert offsets.ndim == 1 and len(offsets) >= 1
            assert offsets[0] == 0 and offsets[-1] == len(points) and np.all(np.diff(offsets) >= 0)
            count = len(offsets) - 1
            families = d['family'].tolist() if 'family' in d else ['unspecified'] * count
            ids = d['chain_ids'].tolist() if 'chain_ids' in d else [str(i) for i in range(count)]
            assert len(families) == len(ids) == count
            curves = [{'id': str(ids[i]), 'family': str(families[i]),
                       'points_xyz': points[offsets[i]:offsets[i + 1]].tolist()} for i in range(count)]
        return curves, {}
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data, {}
    assert isinstance(data, dict) and isinstance(data['curves'], list)
    return data['curves'], {k: v for k, v in data.items() if k != 'curves'}


def sample_predictions(curves, ref, parameters, coordinates):
    chains, inside_parts, inside_labels = [], [], []
    seen_ids = set()
    for i, curve in enumerate(curves):
        chain_id = str(curve.get('id', i))
        assert chain_id not in seen_ids
        seen_ids.add(chain_id)
        points = np.asarray(curve['points_xyz'], dtype=np.float64).reshape(-1, 3)
        assert np.all(np.isfinite(points))
        if coordinates == 'global-xyz':
            points = points - ref.origin_xyz
        family, records, arc0 = str(curve.get('family', 'unspecified')), [], 0.0
        for edge_index, (a, b) in enumerate(zip(points, points[1:])):
            length = float(np.linalg.norm(b - a))
            if length <= EPS:
                continue
            clipped = clip_parameters(a, b, ref.size_xyz)
            if clipped is None:
                intervals = [(0.0, 1.0, False)]
            else:
                lo, hi = clipped
                intervals = [(0.0, lo, False), (lo, hi, True), (hi, 1.0, False)]
            for lo, hi, is_inside in intervals:
                for sa, sb, ss, se in sample_piece(a, b, arc0, lo, hi, parameters.max_step_vox):
                    midpoint = (sa + sb) * 0.5
                    records.append({'a': sa, 'b': sb, 'mid': midpoint, 'start': ss, 'end': se,
                                    'inside': is_inside, 'input_edge_start_index': edge_index,
                                    'boundary': boundary_distance(midpoint, ref.size_xyz) <= parameters.boundary_band_vox})
                    if is_inside:
                        inside_parts.append([sa, sb])
                        inside_labels.append(i)
            arc0 += length
        chains.append({'chain_id': chain_id, 'family': family, 'length': arc0, 'records': records,
                       'point_count': len(points), 'declared_gap_point_ranges': curve.get('gaps', [])})
    return chains, np.asarray(inside_parts, dtype=float).reshape(-1, 2, 3), np.asarray(inside_labels, int)


def coverage_metrics(ref, chains, predicted_index, parameters):
    weights = ref.arc_ends - ref.arc_starts
    hits = []
    for segment in ref.segments:
        ids, distances = predicted_index.nearby(segment.mean(0))
        ids = ids[distances <= parameters.radius_vox + EPS]
        hits.append(set(predicted_index.labels[ids].tolist()))
    covered = np.asarray([bool(h) for h in hits], dtype=bool)
    path_results = []
    for path in ref.paths:
        active, totals = {}, defaultdict(float)
        longest_same, longest_union, union_current, union_runs = 0.0, 0.0, 0.0, 0
        longest_chain, previous_end, previous_hit, covered_length = None, None, False, 0.0
        for i in path['sample_indices']:
            w = float(weights[i])
            consecutive = previous_end is not None and abs(ref.arc_starts[i] - previous_end) <= EPS
            if not consecutive:
                active, union_current, previous_hit = {}, 0.0, False
            h = hits[i]
            if h:
                covered_length += w
                union_runs += not previous_hit
                union_current += w
                longest_union = max(longest_union, union_current)
            else:
                union_current = 0.0
            active = {c: active.get(c, 0.0) + w for c in h}
            for c in h:
                totals[c] += w
                if active[c] > longest_same:
                    longest_same, longest_chain = active[c], c
            previous_end, previous_hit = ref.arc_ends[i], bool(h)
        denominator = path['inside_length_vox']
        best_chain = max(totals, key=totals.get) if totals else None
        best_total = totals[best_chain] if best_chain is not None else 0.0
        path_results.append({
            'path_id': path['path_id'], 'tree_id': path['tree_id'],
            'inside_length_vox': denominator, 'covered_length_vox': covered_length,
            'coverage_fraction': covered_length / denominator if denominator > EPS else None,
            'union_covered_run_count': int(union_runs), 'longest_union_covered_run_vox': longest_union,
            'longest_same_chain_covered_run_vox': longest_same,
            'longest_same_chain_fraction': longest_same / denominator if denominator > EPS else None,
            'longest_visible_reference_component_vox': path['longest_visible_component_vox'],
            'same_chain_continuity_of_visible_reference_ceiling':
                longest_same / path['longest_visible_component_vox'] if path['longest_visible_component_vox'] > EPS else None,
            'longest_same_chain_id': chains[longest_chain]['chain_id'] if longest_chain is not None else None,
            'best_single_chain_covered_length_vox': best_total,
            'best_single_chain_fraction': best_total / denominator if denominator > EPS else None,
            'best_single_chain_id': chains[best_chain]['chain_id'] if best_chain is not None else None,
            'supporting_chain_count': len(totals),
        })
    total_length = float(weights.sum())
    covered_length = float(weights[covered].sum())
    by_scope = {}
    for name, mask in [('fully_inside_original_edges', ref.fully_inside),
                       ('boundary_intersecting_original_edges', ~ref.fully_inside),
                       ('roi_boundary_band', ref.boundary_band),
                       ('roi_interior', ~ref.boundary_band)]:
        denominator = float(weights[mask].sum())
        numerator = float(weights[mask & covered].sum())
        by_scope[name] = {'manual_length_vox': denominator, 'covered_length_vox': numerator,
                          'coverage_fraction': numerator / denominator if denominator > EPS else None}
    tree_results = []
    for tree in ref.trees:
        paths = [p for p in path_results if p['tree_id'] == tree['tree_id']]
        denominator = sum(p['inside_length_vox'] for p in paths)
        numerator = sum(p['covered_length_vox'] for p in paths)
        tree_results.append({'tree_id': tree['tree_id'], 'inside_length_vox': denominator,
                             'covered_length_vox': numerator,
                             'coverage_fraction': numerator / denominator if denominator > EPS else None})
    same_total = sum(p['longest_same_chain_covered_run_vox'] for p in path_results)
    best_total = sum(p['best_single_chain_covered_length_vox'] for p in path_results)
    visible_ceiling = ref.summary['sum_path_longest_visible_component_vox']
    return {
        'manual_length_vox': total_length, 'covered_length_vox': covered_length,
        'manual_edge_length_coverage': covered_length / total_length if total_length > EPS else None,
        'sum_path_longest_same_chain_arc_vox': same_total,
        'path_length_weighted_same_chain_continuity': same_total / total_length if total_length > EPS else None,
        'same_chain_continuity_visible_reference_ceiling': ref.summary['same_chain_continuity_ceiling'],
        'same_chain_continuity_of_visible_reference_ceiling': same_total / visible_ceiling if visible_ceiling > EPS else None,
        'sum_path_best_single_chain_covered_length_vox': best_total,
        'path_length_weighted_best_single_chain_coverage': best_total / total_length if total_length > EPS else None,
        'union_covered_run_count': sum(p['union_covered_run_count'] for p in path_results),
        'by_scope': by_scope, 'per_tree': tree_results, 'per_path': path_results,
    }


def support_metrics(ref, chains, manual_index, parameters):
    chain_results, events = [], []
    length_totals = Counter()
    for chain in chains:
        records = chain['records']
        runs = []
        for i, record in enumerate(records):
            tree_code, path_code, edge, distance = None, None, None, None
            if not record['inside']:
                state = 'outside_roi'
            else:
                ids, distances = manual_index.nearby(record['mid'])
                if not len(ids):
                    state = 'unknown_unannotated'
                else:
                    nearest = int(np.argmin(distances))
                    closest_id, d1 = int(ids[nearest]), float(distances[nearest])
                    proposed_tree = int(manual_index.labels[closest_id])
                    different = distances[manual_index.labels[ids] != proposed_tree]
                    d2 = float(different.min()) if len(different) else math.inf
                    if d1 > parameters.radius_vox + EPS:
                        state = 'unknown_unannotated'
                    elif d2 - d1 < parameters.ambiguity_margin_vox - EPS:
                        state = 'ambiguous_between_trees'
                    else:
                        state = 'known_tree'
                        tree_code, path_code = proposed_tree, int(ref.path_codes[closest_id])
                        edge, distance = ref.original_edges[closest_id], d1
            record.update({'state': state, 'tree_code': tree_code})
            w = record['end'] - record['start']
            length_totals[state] += w
            if record['boundary'] and record['inside']:
                length_totals['inside_boundary_band'] += w
            same = runs and runs[-1]['state'] == state and runs[-1]['tree_code'] == tree_code
            if not same:
                runs.append({'state': state, 'tree_code': tree_code, 'start': record['start'],
                             'end': record['end'], 'sample_start': i, 'sample_end': i + 1,
                             'path_codes': set(), 'start_edge': edge, 'end_edge': edge,
                             'boundary_length': 0.0, 'distance_weighted': 0.0, 'max_distance': 0.0})
            run = runs[-1]
            run['end'], run['sample_end'], run['end_edge'] = record['end'], i + 1, edge
            if path_code is not None:
                run['path_codes'].add(path_code)
            run['boundary_length'] += w * record['boundary']
            if distance is not None:
                run['distance_weighted'] += w * distance
                run['max_distance'] = max(run['max_distance'], distance)
        stable = [r for r in runs if r['state'] == 'known_tree' and r['end'] - r['start'] >= parameters.min_support_vox - EPS]
        stable_length = sum(r['end'] - r['start'] for r in stable)
        short_length = sum(r['end'] - r['start'] for r in runs if r['state'] == 'known_tree'
                           and r['end'] - r['start'] < parameters.min_support_vox - EPS)
        length_totals['sustained_known_tree'] += stable_length
        length_totals['short_known_support'] += short_length
        chain_events = []
        for left, right in zip(stable, stable[1:]):
            if left['tree_code'] == right['tree_code']:
                continue
            window_start = max(left['start'], left['end'] - parameters.min_support_vox)
            window_end = min(right['end'], right['start'] + parameters.min_support_vox)
            transition = [r for r in records[left['sample_start']:right['sample_end']]
                          if r['end'] > window_start and r['start'] < window_end]
            category = 'boundary_cross_tree' if any(r['boundary'] for r in transition) else 'interior_cross_tree'
            gap_by_state = Counter()
            for r in records[left['sample_end']:right['sample_start']]:
                gap_by_state[r['state']] += r['end'] - r['start']
            event = {
                'chain_id': chain['chain_id'], 'family': chain['family'], 'category': category,
                'from_tree_id': ref.trees[left['tree_code']]['tree_id'],
                'to_tree_id': ref.trees[right['tree_code']]['tree_id'],
                'left_support_arc_start_vox': left['start'], 'left_support_arc_end_vox': left['end'],
                'right_support_arc_start_vox': right['start'], 'right_support_arc_end_vox': right['end'],
                'left_support_length_vox': left['end'] - left['start'],
                'right_support_length_vox': right['end'] - right['start'],
                'gap_arc_vox': max(0.0, right['start'] - left['end']), 'gap_length_by_state_vox': dict(gap_by_state),
                'left_anchor_xyz': records[left['sample_end'] - 1]['b'].tolist(),
                'right_anchor_xyz': records[right['sample_start']]['a'].tolist(),
                'left_anchor_input_edge_index': records[left['sample_end'] - 1]['input_edge_start_index'],
                'right_anchor_input_edge_index': records[right['sample_start']]['input_edge_start_index'],
                'left_manual_edge_node_ids': left['end_edge'], 'right_manual_edge_node_ids': right['start_edge'],
            }
            events.append(event)
            chain_events.append(event)
        public_runs = []
        for run in runs:
            length = run['end'] - run['start']
            known = run['state'] == 'known_tree'
            public_runs.append({
                'state': run['state'], 'tree_id': ref.trees[run['tree_code']]['tree_id'] if known else None,
                'manual_path_ids': sorted(ref.paths[p]['path_id'] for p in run['path_codes']),
                'arc_start_vox': run['start'], 'arc_end_vox': run['end'], 'length_vox': length,
                'sustained_support': bool(known and length >= parameters.min_support_vox - EPS),
                'boundary_band_length_vox': run['boundary_length'],
                'mean_distance_vox': run['distance_weighted'] / length if known and length > EPS else None,
                'max_distance_vox': run['max_distance'] if known else None,
                'manual_start_edge_node_ids': run['start_edge'], 'manual_end_edge_node_ids': run['end_edge'],
            })
        state_lengths = Counter()
        for run in public_runs:
            state_lengths[run['state']] += run['length_vox']
        chain_results.append({
            'chain_id': chain['chain_id'], 'family': chain['family'], 'point_count': chain['point_count'],
            'declared_gap_point_ranges': chain['declared_gap_point_ranges'],
            'total_length_vox': chain['length'], 'length_by_state_vox': dict(state_lengths),
            'sustained_known_support_length_vox': stable_length, 'short_known_support_length_vox': short_length,
            'sustained_known_run_count': len(stable), 'cross_tree_switch_count': len(chain_events),
            'interior_cross_tree_switch_count': sum(e['category'] == 'interior_cross_tree' for e in chain_events),
            'boundary_cross_tree_switch_count': sum(e['category'] == 'boundary_cross_tree' for e in chain_events),
            'support_runs': public_runs,
        })
    sustained = float(length_totals['sustained_known_tree'])
    interior = sum(e['category'] == 'interior_cross_tree' for e in events)
    boundary = len(events) - interior
    inside = sum(length_totals[s] for s in ['known_tree', 'unknown_unannotated', 'ambiguous_between_trees'])
    return {
        'predicted_chain_count': len(chains), 'eligible_chain_count': sum(c['sustained_known_run_count'] > 0 for c in chain_results),
        'predicted_total_length_vox': sum(c['length'] for c in chains), 'predicted_inside_length_vox': inside,
        'length_by_state_vox': {k: float(length_totals[k]) for k in [
            'known_tree', 'sustained_known_tree', 'short_known_support', 'unknown_unannotated',
            'ambiguous_between_trees', 'outside_roi', 'inside_boundary_band']},
        'sustained_support_fraction_of_inside_prediction': sustained / inside if inside > EPS else None,
        'cross_tree_switch_count': len(events), 'interior_cross_tree_switch_count': interior,
        'boundary_cross_tree_switch_count': boundary,
        'switched_chain_ids': [c['chain_id'] for c in chain_results if c['cross_tree_switch_count'] > 0],
        'interior_switched_chain_ids': [c['chain_id'] for c in chain_results if c['interior_cross_tree_switch_count'] > 0],
        'interior_switches_per_1000_sustained_supported_vox': interior * 1000.0 / sustained if sustained > EPS else None,
        'all_switches_per_1000_sustained_supported_vox': len(events) * 1000.0 / sustained if sustained > EPS else None,
        'events': events, 'per_chain': chain_results,
    }


def evaluate(reference, curves, parameters=Parameters(), coordinates='local-xyz', case=None,
             prediction_metadata=None):
    started = time.monotonic()
    assert coordinates in {'local-xyz', 'global-xyz'}
    ref = reference if isinstance(reference, PreparedReference) else prepare_reference(reference, parameters, case)
    metadata = dict(prediction_metadata or {})
    if 'coordinates' in metadata:
        expected = {'local-xyz': {'local-xyz', 'ROI-local XYZ voxels'},
                    'global-xyz': {'global-xyz', 'global base XYZ voxels'}}[coordinates]
        assert metadata['coordinates'] in expected
    if 'shape_zyx' in metadata:
        assert np.array_equal(metadata['shape_zyx'], ref.size_xyz[::-1])
    if 'case' in metadata and ref.summary['case']:
        assert metadata['case'] == ref.summary['case']
    frame = metadata.get('frame', {})
    if frame:
        assert frame.get('geometry_axes', 'xyz') == 'xyz'
        assert frame.get('coordinates', coordinates) == coordinates
        if 'origin_xyz' in frame:
            assert np.allclose(frame['origin_xyz'], ref.origin_xyz, atol=EPS, rtol=0)
        if 'case' in frame and ref.summary['case']:
            assert frame['case'] == ref.summary['case']
    chains, predicted_parts, predicted_labels = sample_predictions(curves, ref, parameters, coordinates)
    predicted_index = SegmentIndex(predicted_parts, predicted_labels, parameters.radius_vox)
    manual_index = SegmentIndex(ref.segments, ref.tree_codes,
                               parameters.radius_vox + parameters.ambiguity_margin_vox)
    coverage = coverage_metrics(ref, chains, predicted_index, parameters)
    support = support_metrics(ref, chains, manual_index, parameters)
    return {
        'format': 'manual_nml_reference_evaluation', 'version': 1,
        'evaluated_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'parameters': asdict(parameters), 'prediction_coordinates': coordinates,
        'prediction_metadata': metadata,
        'reference': {k: v for k, v in ref.summary.items() if k not in {'trees', 'paths'}},
        'metric_scope': {
            'coverage': 'length-weighted <=1 voxel manual-edge midpoint to exact predicted segment distance',
            'connectivity': 'observed sustained tree-ID switches along each predicted chain',
            'continuity': 'same predicted-chain geometric coverage runs on original maximal nonbranch manual paths',
            'unknown': 'separate unknown/unannotated and inter-tree ambiguous arcs',
            'native_replay_execution_count': 0,
        },
        'coverage': coverage, 'connectivity': support,
        'elapsed_seconds': time.monotonic() - started,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--predictions', '--traces', dest='predictions', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case')
    parser.add_argument('--prediction-coordinates', choices=['local-xyz', 'global-xyz'], default='local-xyz')
    parser.add_argument('--radius', type=float, default=2.0)
    parser.add_argument('--ambiguity-margin', type=float, default=1.0)
    parser.add_argument('--min-support', type=float, default=8.0)
    parser.add_argument('--max-step', type=float, default=1.0)
    parser.add_argument('--boundary-band', type=float, default=2.0)
    parser.add_argument('--provenance', type=Path, help='Same-frame probability/model identity JSON; retained verbatim')
    parser.add_argument('--summarize', action='store_true', help='Reference integrity and geometry only')
    args = parser.parse_args()
    parameters = Parameters(args.radius, args.ambiguity_margin, args.min_support, args.max_step, args.boundary_band)
    raw = args.reference.read_bytes()
    reference = json.loads(raw)
    case = args.case or args.reference.parent.name
    prepared = prepare_reference(reference, parameters, case)
    if args.summarize:
        result = prepared.summary
    else:
        if args.predictions is None:
            parser.error('--predictions is required for measured output geometry')
        curves, metadata = load_predictions(args.predictions)
        if args.provenance:
            metadata['probability_provenance'] = json.loads(args.provenance.read_text())
        metadata['prediction_file_sha256'] = hashlib.sha256(args.predictions.read_bytes()).hexdigest()
        result = evaluate(prepared, curves, parameters, args.prediction_coordinates, case, metadata)
    result['reference_json_sha256'] = hashlib.sha256(raw).hexdigest()
    source_path = args.reference.parent / 'reference.nml.source.json'
    if source_path.exists():
        result['manual_nml_source_receipt'] = json.loads(source_path.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({'output': str(args.output), 'case': case,
                      'coverage': result.get('coverage', {}).get('manual_edge_length_coverage'),
                      'same_chain_continuity': result.get('coverage', {}).get('path_length_weighted_same_chain_continuity'),
                      'interior_switches': result.get('connectivity', {}).get('interior_cross_tree_switch_count'),
                      'boundary_switches': result.get('connectivity', {}).get('boundary_cross_tree_switch_count')}))


if __name__ == '__main__':
    main()
