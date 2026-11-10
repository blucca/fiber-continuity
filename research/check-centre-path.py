"""Minimal actual-core fixtures: DP objective, world geometry, bounded operator."""
import itertools
import json
from pathlib import Path
import sys
import numpy as np

R = Path(__file__).resolve().parent
sys.path.insert(0, str(R))
from centre_path import recenter_pair, viterbi, path_objective, PARAMETERS

# A small exhaustive fixture verifies the exact integrated-energy optimum.
arc = np.arange(6., dtype=float)
vectors = np.broadcast_to(np.array([[-.5, 0., 0.], [0., 0., 0.], [.5, 0., 0.]]), (6, 3, 3)).copy()
energy = np.array([[0., 1., 0.], [3.2, 1., 3.], [3., 1., 3.2], [3.2, 1., 3.], [3., 1., 3.2], [0., 1., 0.]])
energy[[0, -1]] = -np.inf
energy[[0, -1], 1] = 1.
indices = viterbi(energy, vectors, arc)
best = max(path_objective(energy, vectors, arc, np.asarray(p))[0] for p in itertools.product(range(3), repeat=6))
assert abs(path_objective(energy, vectors, arc, indices)[0]-best) < 1e-10
assert path_objective(energy, vectors, arc, indices)[0] > path_objective(energy, vectors, arc, np.argmax(energy, axis=1))[0]
# Reordering transverse states at every station preserves the physical optimum.
order = np.array([2, 1, 0])
permuted = viterbi(energy[:, order], vectors[:, order], arc)
assert np.array_equal(vectors[np.arange(6), indices], vectors[:, order][np.arange(6), permuted])

shape = (64, 64, 64)
z, y, x = np.indices(shape)
points = np.c_[np.arange(10., 51.), np.full(41, 32.), np.full(41, 32.)]
trace = {'coordinates': 'ROI-local XYZ voxels', 'shape_zyx': list(shape), 'case': 'synthetic',
         'curves': [{'id': 'single', 'family': 'H', 'gaps': [[15, 16]], 'points_xyz': points.tolist()}]}
prob = np.zeros((4,)+shape, np.float32)
prob[0] = .005
prob[2] = .995
flat = np.full(shape, 70, np.uint8)
outputs, diag = recenter_pair(trace, prob, flat)
assert all(d['curves'][0]['points_xyz'] == points.tolist() for d in outputs.values())
ridge = np.clip(70+100*np.exp(-((y-33.)**2+(z-32.)**2)/2.), 0, 255).astype(np.uint8)
outputs, diag = recenter_pair(trace, prob, ridge)
for mode, result in outputs.items():
    p = np.asarray(result['curves'][0]['points_xyz'])
    assert p[20, 1] > 32.5 and np.array_equal(p[[0, -1]], points[[0, -1]])
    assert result['curves'][0]['gaps'] == [[15, 16]] and result['curves'][0]['id'] == 'single'
    assert len(p) == len(points) and np.linalg.norm(p-points, axis=1).max() <= 1.5+1e-8
prob[0] = .8
prob[2] = .2
outputs, diag = recenter_pair(trace, prob, ridge)
assert all(d['curves'][0]['points_xyz'] == points.tolist() for d in outputs.values())
print(json.dumps({'status': 'passed', 'fixtures': ['exact DP exhaustive optimum', 'world state reordering',
    'actual flat CT identity', 'actual single ridge bounded shift and ID/gaps/endpoints', 'actual gate-empty neutral state'],
    'parameters': PARAMETERS}, indent=2))
