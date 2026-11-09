#!/usr/bin/env python3
"""Apply the completed-run float side-output changes to the pinned predictor.

Upstream: ScrollPrize/villa@c3d9da6fe42c3bb46fd2603ca060845d843296c3,
vesuvius/src/vesuvius/fiber_spline_generator/predict.py.
"""
import hashlib
from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: apply_native_float_patch.py PREDICT_PY OUTPUT_PY")
source, output = map(Path, sys.argv[1:])
original = source.read_bytes()
if hashlib.sha256(original).hexdigest() != "3f0f7e66c332739743bc1a2eb4b94477ad56debd4ce187228152aade26552c5b":
    raise ValueError("pinned predict.py SHA-256 check failed")
text = original.decode()
REPLACEMENTS = [('from vesuvius.models.run.tta import infer_with_tta',
  'def infer_with_tta(*args, **kwargs):\n'
  '    raise RuntimeError("mirror=True outside this fixed no-TTA adapter")'),
 ('dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16', 'dtype=torch.float16'),
 ('torch.zeros((3,) + shape', 'torch.zeros((4,) + shape'),
 ('    mirror: bool = True,', '    mirror: bool = False,\n    float_path: str,'),
 ('    output = np.empty(shape + (3,), dtype=np.uint8)',
  '    output = np.empty(shape + (3,), dtype=np.uint8)\n'
  '    float_output = np.lib.format.open_memmap(float_path, mode="w+", dtype=np.float32, shape=(4,) + '
  'shape)'),
 ('            output[first - pad[0][0] : last - pad[0][0]] = np.moveaxis(np.rint(selected * 255)',
  '            float_output[:, first - pad[0][0] : last - pad[0][0]] = selected\n'
  '            output[first - pad[0][0] : last - pad[0][0]] = np.moveaxis(np.rint(selected[1:] * 255)'),
 ('softmax(0)[1:].to(sums.device)', 'softmax(0).to(sums.device)'),
 ('    return output\n', '    float_output.flush()\n    return output\n')]
for before, after in REPLACEMENTS:
    if before not in text:
        raise ValueError("pinned adapter replacement failed: " + before)
    text = text.replace(before, after)
encoded = text.encode()
actual = hashlib.sha256(encoded).hexdigest()
if actual != "6f3b047a1b6b85d8f4f003005fb9278c64be92e7e10c985182c00058db5c00e6":
    raise ValueError("completed-run adapter SHA-256 check failed")
output.write_bytes(encoded)
print(actual)
