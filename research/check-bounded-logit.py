import sys
from pathlib import Path
import numpy as np
from logit_maps import bounded_maps
from transverse_centering import choose_center

p = np.full((9, 9), .99, np.float32); p[5, 4] = .999
u, v = np.meshgrid((np.arange(9)-4)*.5, (np.arange(9)-4)*.5, indexing='ij')
r2 = u*u+v*v
maps = bounded_maps(p, np.zeros_like(p), r2)
for score in maps.values():
    offset, available = choose_center(score)
    assert available and np.array_equal(offset, [.5, 0.])
old = np.log(p)-r2/8.
assert np.array_equal(choose_center(old)[0], [0., 0.])
assert not choose_center(bounded_maps(np.zeros_like(p), np.zeros_like(p), r2)['probability-only'])[1]
assert np.isfinite(bounded_maps(np.ones_like(p), np.zeros_like(p), r2)['probability-only']).all()
batched = bounded_maps(p[None], np.zeros_like(p)[None], r2)
assert np.array_equal(batched['probability-only'][0], maps['probability-only'])
print('PASS: fixed logit scale overcomes real halfvoxel prior; logP stays; shared controls; gate; clipping; batched operator')
