import numpy as np
from overlap_priority import rank_curves, _pieces

def line(i, a, b, family='V'):
    return {'id': i, 'family': family, 'points_xyz': [a, b], 'gaps': []}

base = line('base', [0, 0, 0], [30, 0, 0])
duplicate = line('copy', [30, .1, 0], [0, .1, 0])
independent = line('new', [0, 8, 0], [20, 8, 0])
ranked, evidence = rank_curves([duplicate, independent, base])
assert [c['id'] for c in ranked] == ['base', 'new', 'copy']
assert evidence['rows'][2]['marginal_arc_vox'] == 0.
assert ranked[0] is base and ranked[1] is independent and ranked[2] is duplicate
other_family = dict(duplicate, id='other-family', family='H')
_, e = rank_curves([base, other_family])
assert all(np.isclose(x['marginal_arc_vox'], 30) for x in e['rows'])
crossing = line('crossing', [15, -15, 0], [15, 15, 0])
_, e = rank_curves([base, crossing])
assert all(np.isclose(x['marginal_arc_vox'], 30) for x in e['rows'])
assert rank_curves([])[0] == []
a = _pieces([[0, 0, 0], [0, 0, 0], [4, 0, 0], [4, 3, 0]])
assert np.isclose(a[2].sum(), 7.)
print('PASS: reversal, duplicated arc, independent path, class separation, crossing, empty, zero-length edge, original geometry')
