#!/usr/bin/env python3
"""Convert original WEBKNOSSOS NML to the frozen evaluator's reference schema.

Standard library only. Nodes stay in the original global XYZ voxel frame;
--origin-xyz supplies the translation to the requested cubic ROI.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def summarize_nml(path, origin_xyz, size):
    origin_xyz = list(map(float, origin_xyz))
    assert len(origin_xyz) == 3 and all(math.isfinite(v) for v in origin_xyz)
    assert isinstance(size, int) and size > 0
    raw = Path(path).read_bytes()
    root = ET.fromstring(raw)
    assert root.tag == 'things', root.tag
    params = root.find('parameters')
    parameters = [
        {'tag': p.tag, 'attributes': dict(p.attrib),
         'children': [{'tag': c.tag, 'attributes': dict(c.attrib)} for c in p]}
        for p in params
    ] if params is not None else []
    groups = {g.attrib['id']: dict(g.attrib)
              for g in root.findall('.//groups//group') if 'id' in g.attrib}
    trees, allnodes, names, tree_ids = [], [], Counter(), set()
    for thing in root.findall('thing'):
        attrs = dict(thing.attrib)
        assert 'id' in attrs and attrs['id'] not in tree_ids
        tree_ids.add(attrs['id'])
        nodes, adjacency = {}, {}
        for node in thing.findall('./nodes/node'):
            a = node.attrib
            nid = int(a['id'])
            assert nid not in nodes
            xyz = [float(a[k]) for k in ('x', 'y', 'z')]
            assert all(math.isfinite(v) for v in xyz)
            local = [xyz[k] - origin_xyz[k] for k in range(3)]
            nodes[nid] = {'id': nid, 'xyz': xyz, 'xyz_local': local,
                          'inside_roi': all(0 <= v < size for v in local),
                          'attributes': dict(a)}
            adjacency[nid] = set()
            allnodes.append(xyz)
        edges, seen_edges = [], set()
        for edge in thing.findall('./edges/edge'):
            u, v = int(edge.attrib['source']), int(edge.attrib['target'])
            assert u in nodes and v in nodes and u != v
            key = (min(u, v), max(u, v))
            assert key not in seen_edges
            seen_edges.add(key)
            adjacency[u].add(v)
            adjacency[v].add(u)
            edges.append({'source': u, 'target': v,
                          'inside_roi': nodes[u]['inside_roi'] and nodes[v]['inside_roi']})
        unseen, components = set(nodes), []
        while unseen:
            stack, count = [unseen.pop()], 0
            while stack:
                u = stack.pop()
                count += 1
                for v in adjacency[u]:
                    if v in unseen:
                        unseen.remove(v)
                        stack.append(v)
            components.append(count)
        names[attrs.get('name', '')] += 1
        trees.append({'attributes': attrs, 'group': groups.get(attrs.get('groupId', '')),
                      'nodes': list(nodes.values()), 'edges': edges,
                      'connected_component_node_counts': components,
                      'max_degree': max(map(len, adjacency.values()), default=0)})
    scale = params.find('scale') if params is not None else None
    spacing = [float(scale.attrib[k]) for k in ('x', 'y', 'z')] if scale is not None else None
    full_cubes = [dict(p.attrib) for p in params.findall('userBoundingBox')
                  if p.attrib.get('name', '').replace(' ', '').lower() == 'fullcube'] if params is not None else []
    return {
        'format': 'WebKnossos NML', 'parameters': parameters, 'groups': groups,
        'tree_count': len(trees), 'node_count': len(allnodes),
        'edge_count': sum(len(t['edges']) for t in trees),
        'inside_node_count': sum(n['inside_roi'] for t in trees for n in t['nodes']),
        'inside_edge_count': sum(e['inside_roi'] for t in trees for e in t['edges']),
        'node_bbox_xyz': [[min(p[k] for p in allnodes) for k in range(3)],
                          [max(p[k] for p in allnodes) for k in range(3)]] if allnodes else None,
        'filename_origin_zyx': origin_xyz[::-1], 'roi_size': size,
        'thing_name_counts': dict(names), 'trees': trees,
        'frame': {'geometry_axes': 'xyz', 'array_axes': 'zyx',
                  'origin_xyz': origin_xyz, 'roi_shape_zyx': [size] * 3,
                  'voxel_size_xyz': spacing,
                  'voxel_size_unit': scale.attrib.get('unit') if scale is not None else None,
                  'full_cube_bounding_boxes': full_cubes},
        'source_nml': {'filename': Path(path).name, 'sha256': hashlib.sha256(raw).hexdigest()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nml', type=Path, required=True)
    parser.add_argument('--origin-xyz', nargs=3, type=float, required=True, metavar=('X', 'Y', 'Z'))
    parser.add_argument('--size', type=int, required=True, help='Cubic ROI side length in voxels')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference = summarize_nml(args.nml, args.origin_xyz, args.size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reference, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: reference[k] for k in ('tree_count', 'node_count', 'edge_count',
                                               'inside_node_count', 'inside_edge_count')}))


if __name__ == '__main__':
    main()
