#!/usr/bin/env python3
"""Six evaluator/comparison checks; optionally write NML/JSON and AFV fixtures."""
import argparse
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

import numpy as np

from evaluate import Parameters, evaluate, prepare_reference
from nml_to_reference import summarize_nml
from afv_to_traces import read_afv
from match_coverage import match_coverage, summary


def toy_reference(specs, origin_xyz=(100, 200, 300), size=64):
    """Hand-authored topology, independent of real CT and manual data."""
    trees = []
    for tree_id, points, edges in specs:
        nodes = [{'id': i + 1, 'xyz_local': list(p),
                  'xyz': (np.asarray(p) + origin_xyz).tolist(),
                  'inside_roi': all(0 <= x < size for x in p)} for i, p in enumerate(points)]
        degrees, es = [0] * len(points), []
        for u, v in edges:
            degrees[u - 1] += 1
            degrees[v - 1] += 1
            es.append({'source': u, 'target': v,
                       'inside_roi': nodes[u - 1]['inside_roi'] and nodes[v - 1]['inside_roi']})
        trees.append({'attributes': {'id': str(tree_id), 'name': 'synthetic manual'},
                      'nodes': nodes, 'edges': es, 'max_degree': max(degrees),
                      'connected_component_node_counts': [len(points)]})
    return {'format': 'WebKnossos NML', 'filename_origin_zyx': list(origin_xyz)[::-1],
            'roi_size': size, 'parameters': [], 'trees': trees, 'tree_count': len(trees),
            'node_count': sum(len(t['nodes']) for t in trees),
            'edge_count': sum(len(t['edges']) for t in trees),
            'inside_node_count': sum(n['inside_roi'] for t in trees for n in t['nodes']),
            'inside_edge_count': sum(e['inside_roi'] for t in trees for e in t['edges'])}


def synthetic_checks():
    p = Parameters()
    a = ('A', [[8, 10, 12], [48, 10, 12]], [(1, 2)])
    b = ('B', [[8, 26, 12], [48, 26, 12]], [(1, 2)])
    branch = ('C', [[30, 44, 32], [10, 44, 32], [50, 44, 32], [30, 60, 32]],
              [(1, 2), (1, 3), (1, 4)])
    reference = toy_reference([a, b, branch])
    prepared = prepare_reference(reference, p, 'synthetic')
    assert prepared.summary['degree3_node_count'] == 1
    assert prepared.summary['maximal_nonbranch_path_count'] == 5
    assert sum(path['edge_count'] for path in prepared.paths) == reference['edge_count']
    curves = [{'id': path['path_id'], 'points_xyz': path['points_xyz']} for path in prepared.paths]
    complete = evaluate(prepared, curves, p)
    assert complete['coverage']['manual_edge_length_coverage'] == 1
    assert complete['coverage']['path_length_weighted_same_chain_continuity'] == 1
    assert complete['connectivity']['cross_tree_switch_count'] == 0

    bridge = evaluate(reference, [{'id': 'bridge', 'points_xyz':
                       [[8, 10, 12], [48, 10, 12], [48, 26, 12], [8, 26, 12]]}], p)
    assert bridge['connectivity']['interior_cross_tree_switch_count'] == 1
    event = bridge['connectivity']['events'][0]
    assert (event['from_tree_id'], event['to_tree_id']) == ('A', 'B')
    assert event['left_support_length_vox'] >= 8 and event['right_support_length_vox'] >= 8
    assert event['gap_length_by_state_vox']['unknown_unannotated'] > 0
    boundary = evaluate(reference, [{'id': 'boundary', 'points_xyz':
                        [[8, 10, 12], [48, 10, 12], [63, 10, 12], [63, 26, 12],
                         [48, 26, 12], [8, 26, 12]]}], p)
    assert boundary['connectivity']['boundary_cross_tree_switch_count'] == 1
    assert boundary['connectivity']['interior_cross_tree_switch_count'] == 0

    unknown = evaluate(reference, [{'id': 'unknown', 'points_xyz':
                       [[8, 52, 52], [48, 52, 52]]}], p)
    assert unknown['connectivity']['length_by_state_vox']['unknown_unannotated'] == 40
    assert unknown['connectivity']['eligible_chain_count'] == 0
    assert unknown['connectivity']['all_switches_per_1000_sustained_supported_vox'] is None
    close = toy_reference([a, ('D', [[8, 12, 12], [48, 12, 12]], [(1, 2)])])
    ambiguous = evaluate(close, [{'id': 'mid', 'points_xyz': [[8, 11, 12], [48, 11, 12]]}], p)
    assert ambiguous['connectivity']['length_by_state_vox']['ambiguous_between_trees'] == 40
    assert ambiguous['connectivity']['eligible_chain_count'] == 0

    single = toy_reference([a])
    local = evaluate(single, [{'id': 'A', 'points_xyz': a[1]}], p)
    global_points = (np.asarray(a[1]) + [100, 200, 300]).tolist()
    global_report = evaluate(single, [{'id': 'A', 'points_xyz': global_points}], p, 'global-xyz')
    assert global_report['coverage']['manual_edge_length_coverage'] == local['coverage']['manual_edge_length_coverage']
    swapped = evaluate(single, [{'id': 'axis-error', 'points_xyz': [xyz[::-1] for xyz in a[1]]}], p)
    assert swapped['coverage']['manual_edge_length_coverage'] < 0.25

    fragmented = evaluate(single, [{'id': 'left', 'points_xyz': [[8, 10, 12], [28, 10, 12]]},
                                   {'id': 'right', 'points_xyz': [[28, 10, 12], [48, 10, 12]]}], p)
    assert fragmented['coverage']['manual_edge_length_coverage'] == 1
    assert abs(fragmented['coverage']['path_length_weighted_same_chain_continuity'] - 0.55) < 1e-8
    assert fragmented['connectivity']['cross_tree_switch_count'] == 0

    paired_reference = toy_reference([a, b])
    rich = {'curves': [{'id': '2', 'points_xyz': b[1]}, {'id': '10', 'points_xyz': a[1]}]}
    lean = {'curves': [{'id': 'bridge', 'points_xyz':
            [[8, 10, 12], [28, 10, 12], [28, 26, 12], [8, 26, 12]]}]}
    for baseline, dp, normalized in ((lean, rich, 'dp'), (rich, lean, 'baseline')):
        matched = match_coverage(paired_reference, baseline, dp, 'synthetic-matched')
        assert matched['normalized'] == normalized and len(matched['rows']) == 4
        assert [c['id'] for c in matched['prefixes']['below']['curves']] == ['10']
        assert [c['id'] for c in matched['prefixes']['above']['curves']] == ['10', '2']
        for row in matched['rows']:
            selected = matched['prefixes'][row['bracket']]['curves']
            assert row[normalized] == summary(evaluate(paired_reference, selected,
                Parameters(radius_vox=float(row['radius_vox']))))
    result = {'status': 'PASS', 'checks': [
        'degree3 identity, original-edge partition and complete coverage',
        'sustained cross-tree bridge with interior/boundary separation',
        'unknown and ambiguous arcs with zero eligible support',
        'XYZ axes and explicit global-to-local origin',
        'full coverage with fragmented same-chain continuity',
        'matched-r2 brackets, string-ID tie and identical r3 prefixes'],
        'synthetic_complete_coverage': 1.0, 'synthetic_bridge_interior_switches': 1,
        'synthetic_fragmented_coverage': 1.0, 'synthetic_fragmented_continuity': 0.55}
    json.dumps(result, allow_nan=False)
    return result, reference, curves


def write_example(folder, reference, curves):
    folder.mkdir(parents=True, exist_ok=True)
    root = ET.Element('things')
    params = ET.SubElement(root, 'parameters')
    ET.SubElement(params, 'experiment', name='synthetic')
    ET.SubElement(params, 'scale', x='7.91', y='7.91', z='7.91', unit='micrometer')
    ET.SubElement(params, 'offset', x='0', y='0', z='0')
    ET.SubElement(params, 'userBoundingBox', name='Full Cube', topLeftX='100',
                  topLeftY='200', topLeftZ='300', width='64', height='64', depth='64')
    for tree in reference['trees']:
        thing = ET.SubElement(root, 'thing', tree['attributes'])
        nodes, edges = ET.SubElement(thing, 'nodes'), ET.SubElement(thing, 'edges')
        for node in tree['nodes']:
            ET.SubElement(nodes, 'node', id=str(node['id']), radius='1.0',
                          **dict(zip(('x', 'y', 'z'), map(str, node['xyz']))))
        for edge in tree['edges']:
            ET.SubElement(edges, 'edge', source=str(edge['source']), target=str(edge['target']))
    nml = folder / 'reference.nml'
    ET.ElementTree(root).write(nml, encoding='utf-8', xml_declaration=True)
    converted = summarize_nml(nml, [100, 200, 300], 64)
    assert converted['edge_count'] == 5 and converted['frame']['voxel_size_xyz'] == [7.91] * 3
    assert prepare_reference(converted).summary['degree3_node_count'] == 1
    (folder / 'reference.json').write_text(json.dumps(converted, indent=2) + '\n')
    (folder / 'traces.json').write_text(json.dumps(curves, indent=2) + '\n')

    # Hand-built reader fixture: one 600-segment fiber crosses three blocks.
    # Real writer/reader parity is separately measured on all 363 author fibers.
    path = folder / 'reader.afv'
    path.unlink(missing_ok=True)
    origin = np.array([7, 11, 13])
    local = np.column_stack([np.linspace(2.5, 600.5, 601),
                             np.full(601, 4.5), np.full(601, 6.5)])
    points = local + origin
    with sqlite3.connect(path) as db:
        db.executescript('''PRAGMA application_id=1447249475;
            PRAGMA user_version=1;
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE fibers(id INTEGER, family TEXT, point_count INTEGER, length REAL);
            CREATE TABLE blocks(fiber_id INTEGER, first_segment INTEGER, points BLOB);''')
        metadata = {'complete': True, 'root': {'coordinate_order': 'XYZ'},
                    'frame': {'vc_open_data_source_coordinate_scale_factor': 1,
                              'vc_open_data_source_original_resolution': 7.91}}
        db.executemany('INSERT INTO metadata VALUES(?,?)',
                       [(k, json.dumps(v)) for k, v in metadata.items()])
        db.execute('INSERT INTO fibers VALUES(?,?,?,?)',
                   (7, 'V', len(points), float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())))
        for first in range(0, len(points) - 1, 256):
            db.execute('INSERT INTO blocks VALUES(?,?,?)',
                       (7, first, points[first:first + 257].astype('<f8').tobytes()))
    imported = read_afv(path, 'synthetic-afv', origin.tolist())
    curve, = imported['curves']
    assert curve['id'] == 'afv/7' and curve['family'] == 'V' and curve['gaps'] == []
    assert np.array_equal(curve['points_xyz'], points - origin)
    assert len(curve['points_xyz']) == 601
    (folder / 'afv-check.json').write_text(json.dumps(
        {'status': 'PASS', 'points': 601, 'blocks': 3, 'binary64_overlap_origin_ID': 'exact'}) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, help='Write hand-authored synthetic NML/JSON here')
    args = parser.parse_args()
    result, reference, curves = synthetic_checks()
    if args.examples:
        write_example(args.examples, reference, curves)
    print(json.dumps(result, indent=2))
