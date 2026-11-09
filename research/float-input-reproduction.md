# Native float-probability handoff to bounded-logit recentering

## Input contract

The generation CLI consumes the original **FP32 four-channel side output** of the native sliding-window predictor:

- CT: uint8 NumPy `.npy`, shape `(Z,Y,X)`, array axes ZYX.
- Probabilities: float32 NumPy `.npy`, shape `(4,Z,Y,X)`, channels **background / vt-fiber / hz-fiber / intersection**.
- Traces: mature extended prediction envelope for the same CT lattice, ROI-local XYZ voxel points; families `V` and `H` select probability channels 1 and 2 and add channel 3.

The completed inference retained these four channels after window-probability blending and before uint8 rounding. Its ordinary native cache contains `(Z,Y,X,3)` uint8 V/H/intersection values, serialized under the `probabilities` NPZ key. A `u8/255` reconstruction is a quantized-input variant and receives its own evaluation.

Precision matters to the fixed logit energy. For an own-family probability `float32(0.999)` with intersection probability 0, the bounded logit of their sum is `6.906767845`; per-channel uint8 rounding produces 255 and 0, and reconstructing their sum 1.0 then applying the same `1e-5` clip yields `11.511557579`. The score difference is about 4.605. This is a source-defined scalar illustration of the input precision contract.

## Immutable upstream inputs

Source: [ScrollPrize/villa@c3d9da6fe42c3bb46fd2603ca060845d843296c3](https://github.com/ScrollPrize/villa/tree/c3d9da6fe42c3bb46fd2603ca060845d843296c3).

Required source files relative to that checkout:

| File | SHA-256 |
| --- | --- |
| `vesuvius/src/vesuvius/fiber_spline_generator/predict.py` | `3f0f7e66c332739743bc1a2eb4b94477ad56debd4ce187228152aade26552c5b` |
| `vesuvius/src/vesuvius/utils/models/load_nnunet_model.py` | `2a86a3d9481f443a5ff34e791ea7d4f45b870382b3b241f1868202edbbffe17d` |

Model: [`scrollprize/fiber_hz_vt@0905e68f14b33d1b98fd32d726f2c97607dea80c`](https://huggingface.co/scrollprize/fiber_hz_vt/tree/0905e68f14b33d1b98fd32d726f2c97607dea80c). Prepare one local flat model directory with these exact files:

| File | SHA-256 |
| --- | --- |
| `checkpoint_final.pth` | `a80d98f1baaaa09fac5e9d499ade91cb6f79982239cf8520fec9c217125ed899` |
| `plans.json` | `52ad3c12d15fe651a4841912287f0cd358f43839889a5b0690186aca0c6aaa93` |
| `dataset.json` | `4b6396a383612c66e391c822ded5341f90dcf59d6af638ccf9a7bf732c8e1039` |

The recorded model is `dynamic_network_architectures.architectures.unet.ResidualEncoderUNet`, one input channel, four segmentation heads, configuration `3d_fullres`, fold 0, native patch **`(256,256,224)` ZYX**, deep supervision disabled, strict checkpoint state-dict load, and compilation disabled. The checkpoint records trainer `nnUNetTrainerMedialSurfaceRecall`; the completed run binds `resolve_python_class_exact` to return `None`, selecting the loader's existing direct plans-architecture branch. Its two additional return fields, `checkpoint_init_args` and `checkpoint_top_level_keys`, serve receipt collection. Export uses the original loader's `network` and `patch_size` fields.

## Exact preprocessing and blend

1. `predict.normalize` copies the whole CT ROI to float32, computes its own mean using plane-wise float64 sums, and computes its own variance using plane-wise float64 squared differences. It divides the centered image by `max(std,10)` gray levels.
2. Model architecture and patch dimensions come from the pinned plans. CT preprocessing is performed by the native predictor. This pass uses identity ZYX ordering and model lattice spacing `[1,1,1]`; the recorded physical CT lattice is isotropic 7.91 µm.
3. Small ROIs receive symmetric edge-value padding up to the model patch. Window stride is `max(1,patch//2)` per axis; the final window is border-aligned.
4. Each `(1,1,*patch)` tile runs with **CUDA FP16 autocast**, `mirror=False`. The network output is converted to FP32; list/tuple outputs use their first logits tensor.
5. Each window applies `logits[0].float().softmax(0)` across **all four channels**. Probabilities are accumulated in FP32 with a separable Gaussian weight: center `(patch-1)/2`, sigma `patch/8`, product floor `1e-4`.
6. Final probability is `weighted_probability_sum / weight_sum`. The predictor unpads rows/columns and writes all four channels directly to the float32 CZYX memory-mapped `.npy`.
7. The same selected probability planes produce the native cache: `moveaxis(rint(selected[1:]*255).clip(0,255).astype(uint8),0,-1)`. The float side output is flushed after the final window row.

The completed source/receipt records float shape `(4,256,256,256)`, range `[1.3344104138828344e-27,1.0]`, maximum channel-sum error `3.5762786865234375e-7`, and exact equality between its native uint8 cache and the specified quantization of its float side output.

## Small adapter changes

`native-predict-float.patch` is the original 74-line generic unified diff. Its hunks:

- Replace the TTA import with a fixed `mirror=True` error guard; default `mirror=False`.
- Select CUDA FP16 autocast explicitly.
- Expand both GPU and CPU-fallback accumulation buffers from 3 to 4 channels.
- Add required keyword-only `float_path: str` to `predict_fibers`.
- Allocate `open_memmap(float_path, mode="w+", dtype=float32, shape=(4,)+ct.shape)`.
- Retain background in each window's softmax.
- Persist all four blended channels before quantizing `selected[1:]` into the original native return array.
- Flush the float memory map before returning.

`apply_native_float_patch.py` reproduces the completed run's exact eight fixed string-replacement operations using Python's standard library. It verifies both the original source hash and the generated adapter hash. Prepared adapter SHA-256: `6f3b047a1b6b85d8f4f003005fb9278c64be92e7e10c985182c00058db5c00e6`.

The patch and apply utility contain generic source changes and user-supplied path arguments. Offline preparation verified byte equality with the completed inference adapter and parsed the generated source as Python.

## Dependency contract

Use Python≥3.10 and a working CUDA-enabled PyTorch environment. The measured direct package versions are:

```text
torch==2.11.0+cu130
numpy==2.1.3
scipy==1.16.3
nnunetv2==2.8.1
dynamic-network-architectures==0.4.4
acvl-utils==0.2.7
batchgenerators==0.25.6
einops==0.8.1
timm==1.0.22
```

The nnU-Net and architecture packages require their normal transitive dependencies as declared in their package metadata. Use normal dependency resolution for those pinned packages in a compatible CUDA PyTorch environment. Adapter preparation itself uses Python's standard library. The bounded-recenter stage uses NumPy/SciPy and the published sibling modules.

## Reusable command sequence

Run these commands in a user-controlled working directory containing the `fiber-continuity` checkout, the pinned source checkout `./villa`, a matched local model `./model`, `ct.npy`, and mature `extended.json`.

First produce the exact float predictor source:

```sh
python3 fiber-continuity/research/apply_native_float_patch.py \
  villa/vesuvius/src/vesuvius/fiber_spline_generator/predict.py \
  native_predict_float_adapter.py
```

Then run the original pinned model loader and the float adapter. This is the reproduction command for a future operator; preparation of this card performed source-only checks.

```sh
nnUNet_compile=false python3 - <<'PY'
import hashlib
import importlib.util
from pathlib import Path
import sys
import numpy as np
import torch

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

model = Path("model")
expected = {
    "checkpoint_final.pth": "a80d98f1baaaa09fac5e9d499ade91cb6f79982239cf8520fec9c217125ed899",
    "plans.json": "52ad3c12d15fe651a4841912287f0cd358f43839889a5b0690186aca0c6aaa93",
    "dataset.json": "4b6396a383612c66e391c822ded5341f90dcf59d6af638ccf9a7bf732c8e1039",
}
for name, digest in expected.items():
    h = hashlib.sha256()
    with (model/name).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            h.update(block)
    assert h.hexdigest() == digest, name

loader_path = Path("villa/vesuvius/src/vesuvius/utils/models/load_nnunet_model.py")
assert hashlib.sha256(loader_path.read_bytes()).hexdigest() == "2a86a3d9481f443a5ff34e791ea7d4f45b870382b3b241f1868202edbbffe17d"
loader = load_module("pinned_fiber_loader", loader_path)
loader.resolve_python_class_exact = lambda *args, **kwargs: None
info = loader.load_model_for_inference(model_folder=str(model), fold=0,
    checkpoint_name="checkpoint_final.pth", device_str="cuda", verbose=False)
assert info["num_input_channels"] == 1 and info["num_seg_heads"] == 4
assert tuple(info["patch_size"]) == (256, 256, 224)

predictor = load_module("native_predict_float_adapter", Path("native_predict_float_adapter.py"))
ct = np.load("ct.npy", allow_pickle=False)
assert ct.dtype == np.uint8 and ct.ndim == 3
native = predictor.predict_fibers(info["network"], ct, info["patch_size"],
    device=torch.device("cuda:0"), mirror=False, float_path="probabilities-czyx-f32.npy")
torch.cuda.synchronize()
np.savez_compressed("native-probabilities-zyxc3-u8.npz", probabilities=native)
p = np.load("probabilities-czyx-f32.npy", mmap_mode="r", allow_pickle=False)
assert p.dtype == np.float32 and p.shape == (4,) + ct.shape
print({"probabilities_shape": p.shape, "dtype": str(p.dtype), "channels": ["background", "V", "H", "intersection"]})
PY

python3 fiber-continuity/research/bounded_logit_recenter.py \
  --ct ct.npy --probabilities probabilities-czyx-f32.npy \
  --traces extended.json --output raw.json
```

The raw envelope then enters the existing pinned native cleanup with angle 45°, minimum length 100 vox, and exterior-black distance 16 vox. `--mode probability-only` selects the matched probability control with the same float input.

## Published operator handoff

[`native-predict-float.patch`](native-predict-float.patch) and
[`apply_native_float_patch.py`](apply_native_float_patch.py) contain the fixed,
generic source transformation. The bounded-recenter CLI was frozen at
[`f88e8894fa7dad1a56f670796f893a6793618faa`](https://github.com/blucca/fiber-continuity/tree/f88e8894fa7dad1a56f670796f893a6793618faa);
its [s5 controls and first s1 postprocessor holdout](bounded-logit-study.md)
use FP32 CZYX4. Quantized native-u8 variant evaluations: 0. These handoff files
provide the already-measured input operator; postprocessor parameters and
training remain unchanged. Original CT/probability geometry stays with its
operator. Obtain data and models through the linked upstream sources.
