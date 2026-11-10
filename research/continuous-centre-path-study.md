# Continuous centre-path optimization

Status: **fixed research method; the following four-cube development snapshot is preserved.** The [first two new-spatial validation results](continuous-path-spatial-validation.md) now pass the published native-clean radius2 gate; all radius3 and negative results are recorded. At the immutable source freeze, their reference-performance/image reads were0.

The centre path jointly chooses 29 transverse states every ≤1 voxel along the original arc. Each state is within 1.5 voxels of the mature spline/MLP trace. Unary evidence is fixed-model family+intersection logit plus CT DoG/MAD, with the original radial prior and probability gate. The integrated score uses original-arc trapezoid weights. Dynamic programming maximizes it minus `2 |d_i−d_(i−1)|² / Δs`, where displacement differences are in world XYZ and stay invariant to transverse-frame state ordering. The finite-state optimum is evaluated before the shared Gaussian post-smoother. All reported geometry metrics use the final smoothed output.

The causal control selects the highest unary at exactly the same stations. Both operators share finite-domain context, zero fallback, pinned endpoints, fixed σ2 smoother, original knots/IDs/gaps, and the native 45°/100-voxel/16-voxel-black cleanup. Topology edits: 0. The older Gaussian-at-original-knots method retains its separate four-cube failure report.

## Complete development comparison

All four cases were inspected by earlier methods, so they are development data for this method. No grid search was run. Radius2 common coverage uses longest-first whole-curve lower/upper brackets; the richer output is reduced, including baseline when it has greater coverage. Radius3 reuses the identical prefixes.

| Case | Stage | Reduced output | DP−baseline coverage pp, lower / upper | Relative continuity change, lower / upper | Interior switches DP/baseline, lower / upper |
|---|---|---|---:|---:|---|
| s5_03997_01497_03997_256 | raw | dp | -0.0557 / +0.1039 | +9.386% / +9.386% | 0/0 / 0/0 |
| s5_03997_01497_03997_256 | clean | dp | -0.3569 / +0.2713 | +3.182% / +6.922% | 0/0 / 0/0 |
| s1_00497_02497_02997_256 | raw | dp | -0.0120 / +0.0261 | +3.732% / +3.776% | 2/3 / 2/3 |
| s1_00497_02497_02997_256 | clean | dp | -0.3433 / +0.0154 | +2.225% / +3.067% | 2/3 / 2/3 |
| s1_10997_02997_02997_256 | raw | dp | -0.0521 / +0.0163 | +1.520% / +1.520% | 3/3 / 3/3 |
| s1_10997_02997_02997_256 | clean | dp | -0.2636 / +0.0422 | +1.847% / +3.297% | 0/1 / 1/1 |
| s5_14997_01497_01497_256 | raw | baseline | +0.0369 / -0.0225 | -4.176% / -4.394% | 2/2 / 2/2 |
| s5_14997_01497_01497_256 | clean | baseline | +0.2845 / -0.0318 | -3.939% / -3.953% | 1/1 / 1/1 |

Boundary switches are 0 in all development rows. Radius2 continuity increases in the first three cubes and decreases in the fourth. In s1_00497, raw radius3 switches are 5 versus 4; clean switches are 2 versus 3 at both radii. In s1_10997, the clean lower prefix has 0 versus 1 interior switch, while the upper has 1 versus 1. These prefixes preserve their own counts. Radius3 sensitivity has negative clean continuity in the first three cubes and positive continuity in the fourth; its coverage differences are reported explicitly.

[Every full and matched aggregate row](centre-path-development-results.json), including supported/unknown/ambiguous arc and eligible chains, is published. The evaluator is the unchanged v1 source. The fixed segmentation training membership is a separate model-provenance field; heldout here covers the postprocessor parameters.

## Execute the measured geometry

Python 3.10+ with NumPy and SciPy. Input CT is uint8 ZYX; probabilities are float32 (4,Z,Y,X), channel order background/V/H/intersection. Mature raw traces use ROI-local XYZ voxels and the existing envelope fields. The command opens these three inputs.

```bash
python -m pip install numpy scipy
python research/check-centre-path.py
python research/run_centre_path.py --ct data/ct.npy \
  --probabilities data/probabilities-czyx-f32.npy \
  --traces data/extended.json --output temp/centre-path
python evaluate.py --reference data/reference.json \
  --traces temp/centre-path/dp-raw.json --radius 2 \
  --output temp/centre-path/dp-raw.metrics-r2.json
```

The command writes both `dp-raw.json` and `pointwise-raw.json`, plus aggregate diagnostics. For native cleanup, use the pinned upstream `vesuvius.fiber_spline_generator.cleanup.clean` with max_angle45/min_length100 and `ExteriorBlack` constructed from the same CT block at local origin0; black_distance16. Map `V/H` to native family0/1 and preserve source IDs and gaps. Evaluate the resulting clean envelope with the same reference and compare lower/upper coverage brackets. Baseline/model and float-export reproduction are linked in [README](../README.md) and [float input reproduction](float-input-reproduction.md).

## Frozen first new-spatial validation

[The source and parameter manifest](centre-path-freeze.json) fixes all algorithm inputs, source files, evaluator/native pins, two case filenames, and the gate before their first reference scoring. Primary endpoint is clean radius2 matched continuity in both brackets on **both** new cases, with observed clean interior/boundary switches no greater at r2/r3 in either bracket. Publish all raw and clean rows at both radii. Reference performance and image reads at freeze: 0. Heldout parameter tuning: 0.

Deployment promotion remains stopped pending this full gate and the native consumption stage. Research code and synthetic checks use MIT; acquire raw CT/NML through the official data source.
