#!/usr/bin/env python3
"""Five small synthetic checks; optionally write a synthetic CLI example."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from evaluate import Parameters, evaluate, prepare_reference
from nml_to_reference import summarize_nml


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
    result = {'status': 'PASS', 'checks': [
        'degree3 identity, original-edge partition and complete coverage',
        'sustained cross-tree bridge with interior/boundary separation',
        'unknown and ambiguous arcs with zero eligible support',
        'XYZ axes and explicit global-to-local origin',
        'full coverage with fragmented same-chain continuity'],
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, help='Write hand-authored synthetic NML/JSON here')
    args = parser.parse_args()
    result, reference, curves = synthetic_checks()
    if args.examples:
        write_example(args.examples, reference, curves)
    print(json.dumps(result, indent=2))
