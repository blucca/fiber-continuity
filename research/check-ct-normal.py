"""Minimal numerical check: native XYZ, flat/boundary context, independent normal."""
import json
import numpy as np
from ct_normal_diagnostic import ct_normal, sheet_frame

z, y, x = np.indices((49, 49, 49))
ct = (80 + 20 * np.cos((x - 24) * np.pi / 8)).astype(np.float32)
normal, values = ct_normal(ct, [24., 24., 24.])
assert normal[0] > .999 and values[-1] > 100 * max(values[-2], 1e-12)
assert ct_normal(np.full(ct.shape, 80, dtype=np.float32), [24, 24, 24]) is None
assert ct_normal(ct, [0, 24, 24]) is None
assert sheet_frame(normal, normal) is None
before = normal.copy()
t = np.array([.5, np.sqrt(.75), 0.])
inplane, lateral = sheet_frame(normal, t)
assert np.array_equal(normal, before)
assert abs(inplane @ normal) < 1e-12 and abs(lateral @ normal) < 1e-12
assert np.isclose(np.linalg.norm(inplane), 1)
assert np.isclose(np.linalg.norm(lateral), 1)
assert np.isclose(np.degrees(np.arcsin(abs(normal @ t))), 30)
print(json.dumps({'status': 'PASS', 'checks': ['native XYZ tensor normal', 'flat and boundary context',
    'vanishing sheet direction', 'CT normal retained with off-sheet tangent']}))
