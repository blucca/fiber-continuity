# Bounded logit-plus-CT recentering: development freeze

The frozen main method retains the mature spline/MLP curve topology and
recentres within 1.5 vox using logit probability plus normalized CT contrast.
On s5, the radius 2 matched-below raw prefix improves same-chain continuity
by 9.76%; the matched-below clean prefix improves it by 2.75%.
Radius 3 on those same prefixes has lower coverage; its clean continuity
also decreases. This publication freezes the method before the first s1
coverage/connectivity evaluation. Added-flow / ownership / native-augmentation
results remain in the [separate side study](overlap-ownership-study.md).

## Input and score scale

1. Reuse all 324 mature threshold 60 MLP-extended polylines from
   [pinned villa@c3d9da6fe42c3bb46fd2603ca060845d843296c3](https://github.com/ScrollPrize/villa/tree/c3d9da6fe42c3bb46fd2603ca060845d843296c3),
   generated from the fixed
   [fiber_hz_vt checkpoint](https://huggingface.co/scrollprize/fiber_hz_vt/tree/0905e68f14b33d1b98fd32d726f2c97607dea80c).
   Inputs are uint8 CT ZYX, float32 probability CZYX4
   (background / V / H / intersection), and existing predicted curves in
   ROI-local XYZ voxels. The original physical spacing is 7.91 µm.
2. Use the preceding 8-vox original-arc tangent, with forward fallback at the
   start, to construct a deterministic transverse frame. A 33×33 profile on
   a 0.5-vox grid covers radius 8. Trilinear sampling uses `nearest` mode.
   A profile outside the finite `[0,size−1]` lattice contributes zero selected
   displacement before the shared arc smoothing.
3. Smooth CT isotropically with Gaussian sigma 1 voxel, truncate 4. Subtract an
   additional transverse Gaussian sigma 2 voxel background, truncate 2.
   Normalize the resulting DoG by `max(1.4826*MAD_radius6,1 gray level)`.
4. `Pf = P(own V/H class) + P(full intersection)`. Gate at `Pf≥0.5`.
   Clip Pf to `[1e-5,1−1e-5]` and use
   `logit(Pf)=log(Pf)−log(1−Pf)`. The two complete controls are:

   ```text
   probability-only   = logit(Pf) − radial_squared/8
   ct-energy-control  = logit(Pf) + CT_DoG/MAD_scale − radial_squared/8
   ```

   Both choose a candidate only within radius 1.5 on the same 0.5-vox grid.
   Nearest incoming-centre position resolves exact-score ties.
5. Smooth displacements along the original arc with Gaussian sigma 2 vox on
   a grid of max step 0.5, truncate 4 / nearest. Reproject perpendicular to the
   frozen original tangent; radius-cap and clip along that vector to the
   finite volume. Pin both endpoints. Preserve raw source IDs, point count,
   point order and gaps. Cross-curve connection creation is 0.
6. Apply unchanged native cleanup 45° / minimum 100 vox / exterior black 16 vox,
   then the frozen evaluator. Manual annotations enter evaluation only.

The probability scale is the sole new score mechanism relative to the earlier
bounded logP control: logP(0.999)−logP(0.99)≈0.00905, while the half-voxel prior
costs 0.03125. The logit difference is ≈2.31. The synthetic scale check captures
that exact comparison; the complete real controls below measure its effect.

## Complete s5 outputs

Manual visible-reference arc is 15,654.564 vox. Radius 2 is primary, radius 3
sensitivity. Raw outputs keep all 324 curves in both controls; cleanup retains
56 P-only curves and 57 CT-control curves. Every row records 0 interior /
0 boundary observed tree-ID switches on manual sustained known support.

| Radius | Stage | Mature MLP C / continuity | Logit P-only C / continuity | Logit + CT C / continuity |
|---:|---|---:|---:|---:|
| 2 | raw | 0.381040 / 0.195376 | 0.388963 / 0.208022 | 0.398840 / 0.218277 |
| 2 | clean | 0.278677 / 0.160557 | 0.284250 / 0.166671 | 0.300185 / 0.177434 |
| 3 | raw | 0.564750 / 0.336138 | 0.569143 / 0.338561 | 0.571548 / 0.339022 |
| 3 | clean | 0.418161 / 0.276466 | 0.421903 / 0.278059 | 0.429529 / 0.280841 |

C denotes manual arc coverage; continuity is the unnormalized
path-length-weighted same-chain fraction. The evaluator also reports its
visible-reference-ceiling normalization; the visible s5 ceiling is 0.9674907193.
Unknown/unannotated arc retains a separate denominator and is included below.

## Matched coverage: CT-control brackets

Whole-curve length-descending / stable-ID prefixes bracket the mature MLP
baseline coverage at radius 2, independently for raw and cleaned output.
Bracketing is evaluation normalization after prediction generation;
reference geometry supplies that target, and the recentering receives CT,
probabilities and predictions only. Radius 3 evaluates those same radius 2
prefixes.

| Radius / baseline stage | C | Continuity | Sustained known arc (vox) | Unknown arc (vox) |
|---|---:|---:|---:|---:|
| 2 / raw | 0.381040 | 0.195376 | 5412.715 | 12890.773 |
| 2 / clean | 0.278677 | 0.160557 | 4041.766 | 6958.827 |
| 3 / raw | 0.564750 | 0.336138 | 8239.379 | 10251.468 |
| 3 / clean | 0.418161 | 0.276466 | 6257.501 | 4887.625 |

| CT-control prefix | Curves | Radius | Manual coverage | Same-chain continuity | Sustained known arc (vox) | Unknown arc (vox) |
|---|---:|---:|---:|---:|---:|---:|
| raw below | 179 | 2 | 0.380567 | 0.214440 | 5556.059 | 11116.802 |
| raw below | 179 | 3 | 0.544938 | 0.335949 | 7997.623 | 8694.665 |
| raw above | 180 | 2 | 0.382120 | 0.214440 | 5577.627 | 11116.802 |
| raw above | 180 | 3 | 0.546606 | 0.335949 | 8019.191 | 8694.665 |
| clean below | 51 | 2 | 0.275279 | 0.164974 | 4030.337 | 6566.009 |
| clean below | 51 | 3 | 0.400408 | 0.263888 | 5961.039 | 4690.300 |
| clean above | 52 | 2 | 0.281728 | 0.170856 | 4129.135 | 6580.975 |
| clean above | 52 | 3 | 0.407886 | 0.270307 | 6073.847 | 4691.256 |

The raw 179-curve lower bracket gives **C 0.380567 / continuity 0.214440**
versus baseline **0.381040 / 0.195376** (+9.76% continuity); the 180-curve
upper bracket has C 0.382120 and the same continuity.

The clean 51-curve lower bracket gives **C 0.275279 / continuity 0.164974**
versus baseline **0.278677 / 0.160557** (+2.75% continuity); clean 52 gives
C 0.281728 / continuity 0.170856. The radius 2 clean lower bracket has sustained
known arc 4,030.337 vox and unknown arc 6,566.009 vox.

**Sensitivity boundary:** radius 3 raw 179 has C 0.544938 / continuity 0.335949
versus 0.564750 / 0.336138. Clean 51 has C 0.400408 / 0.263888 versus
0.418161 / 0.276466; clean 52 has C 0.407886 / 0.270307. Both cleaned prefixes
have lower radius 3 coverage and continuity. The positive development result
is the radius 2 matched-coverage comparison reported above.

### Shared probability-only causal control

| Probability control | Curves | Radius | Manual coverage | Same-chain continuity | Sustained known arc (vox) | Unknown arc (vox) |
|---|---:|---:|---:|---:|---:|---:|
| raw probability-only below | 231 | 2 | 0.380914 | 0.207709 | 5548.623 | 11978.939 |
| raw probability-only below | 231 | 3 | 0.556586 | 0.338371 | 8174.803 | 9403.206 |
| clean probability-only below | 55 | 2 | 0.277951 | 0.162490 | 4101.632 | 6896.880 |
| clean probability-only below | 55 | 3 | 0.414879 | 0.273525 | 6199.158 | 4854.186 |

The probability-only lower brackets improve radius 2 continuity to 0.207709
(raw 231) and 0.162490 (clean 55); adding normalized CT raises it further in
the selected main configuration. Radius 3 clean 55 has continuity 0.273525
versus baseline 0.276466. Controls and radius sensitivity remain explicit.

## Run the published generation and small checks

[`logit_maps.py`](logit_maps.py) supplies both score maps.
[`bounded_logit_recenter.py`](bounded_logit_recenter.py) exposes the complete
fixed-topology raw generation primitive and CLI. The default mode is the
frozen `ct-energy-control`; `--mode probability-only` runs its causal control.
Upstream native cleanup is a subsequent stage.

```bash
python -m pip install numpy scipy
python research/check-bounded-logit.py
python research/check-recenter.py
python research/bounded_logit_recenter.py \
  --ct data/ct.npy --probabilities data/probabilities-czyx4.npy \
  --traces data/mature-extended.json --output results/recentered-raw.json
```

Synthetic checks cover logit/prior scaling, shared controls, gate/clipping,
flat-field identity, a bright ridge, endpoint pins, unchanged IDs/gaps/point
counts, and incomplete transverse context. Published source uses the measured
score and geometry rules; real CT/probability/reference geometry is kept in
research caches. Source/data attribution and licensing follow the main README.

## Freeze and next validation

This main configuration is frozen after the completed s5 controls and matched
comparison, before the first s1 coverage/connectivity measurement. The frozen
method keeps the original mature geometry as its topology anchor; new flow,
ownership and native-link augmentation are excluded from that recipe.
Same-chain improvements apply to the measured s5/radius 2 scope; s1 is the
next frozen-method evaluation. Method superiority, external adoption and
awards have each recorded 0 at this development freeze. Surface fitting,
flattening and VC3D rendering remain subsequent native-consumer checkpoints.
