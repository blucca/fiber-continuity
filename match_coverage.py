#!/usr/bin/env python3
"""Fixed r2 whole-curve coverage brackets; identical prefixes at r3.

Inputs share one reference and ROI-local XYZ frame; run raw/clean separately.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import evaluate as E


def summary(metric):
    c, s = metric['coverage'], metric['connectivity']
    return {'coverage': c['manual_edge_length_coverage'],
            'continuity': c['path_length_weighted_same_chain_continuity'],
            'interior_switches': s['interior_cross_tree_switch_count'],
            'boundary_switches': s['boundary_cross_tree_switch_count'],
            'supported_vox': s['length_by_state_vox']['sustained_known_tree'],
            'unknown_vox': s['length_by_state_vox']['unknown_unannotated'],
            'ambiguous_vox': s['length_by_state_vox']['ambiguous_between_trees'],
            'eligible_chains': s['eligible_chain_count'], 'count': s['predicted_chain_count']}


def length(curve):
    points = np.asarray(curve['points_xyz'], dtype=float).reshape(-1, 3)
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def match_coverage(reference, baseline, dp, case):
    prepared = {r: E.prepare_reference(reference, E.Parameters(radius_vox=float(r)), case)
                for r in (2, 3)}
    assert prepared[2].summary['inside_manual_arc_vox'] > 0, 'Positive visible manual arc required'
    envelopes = {'baseline': baseline, 'dp': dp}

    def measure(envelope, radius):
        return summary(E.evaluate(prepared[radius], envelope['curves'],
            E.Parameters(radius_vox=float(radius)), case=case,
            prediction_metadata={k: v for k, v in envelope.items() if k != 'curves'}))

    full = {mode: {r: measure(envelope, r) for r in (2, 3)}
            for mode, envelope in envelopes.items()}
    target = min(full['baseline'][2]['coverage'], full['dp'][2]['coverage'])
    normalized = 'dp' if full['dp'][2]['coverage'] > full['baseline'][2]['coverage'] else 'baseline'
    curves = sorted(envelopes[normalized]['curves'], key=lambda c: (-length(c), str(c['id'])))
    rule = 'r2 wholecurve common-C lower/upper; identical prefix at r3'

    def prefix(n):
        # Describe the selected archive, including its length, in the prefix metadata.
        return dict(envelopes[normalized], curves=curves[:n], count=n, normalization=rule,
                    length_voxels=sum(length(c) for c in curves[:n]))

    lo, hi, searches = 0, len(curves), []
    bounds = {0: 0., hi: full[normalized][2]['coverage']}
    while hi - lo > 1:
        n = (lo + hi) // 2
        measured = measure(prefix(n), 2)
        searches.append({'count': n, **measured})
        bounds[n] = measured['coverage']
        if measured['coverage'] <= target:
            lo = n
        else:
            hi = n
    assert bounds[lo] <= target <= bounds[hi]
    prefixes, rows = {}, []
    for bracket, n in [('below', lo), ('above', hi)]:
        prefixes[bracket] = prefix(n)
        for radius in (2, 3):
            pair = {mode: full[mode][radius] for mode in envelopes}
            pair[normalized] = measure(prefixes[bracket], radius)
            rows.append({'case': case, 'radius_vox': radius, 'bracket': bracket,
                'normalized': normalized, 'count': n, **pair,
                'coverage_difference_pp': 100 * (pair['dp']['coverage'] - pair['baseline']['coverage']),
                'continuity_difference': pair['dp']['continuity'] - pair['baseline']['continuity']})
    return {'case': case, 'normalization': rule, 'target_coverage_r2': target,
            'normalized': normalized, 'parameters': {r: asdict(E.Parameters(radius_vox=float(r)))
                for r in (2, 3)}, 'full': full, 'prefixes': prefixes, 'rows': rows, 'searches': searches}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--dp', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs = {name: getattr(args, name) for name in ('reference', 'baseline', 'dp')}
    envelopes = {}
    for mode in ('baseline', 'dp'):
        curves, metadata = E.load_predictions(inputs[mode])
        envelopes[mode] = dict(metadata, curves=curves)
    result = match_coverage(json.loads(args.reference.read_text()),
                            envelopes['baseline'], envelopes['dp'], args.case)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(args.output), 'normalized': result['normalized'], 'rows': 4}))


if __name__ == '__main__':
    main()
