# Bounded logit-plus-CT recentering: development freeze

The complete main method includes unchanged native cleanup and retains
the mature spline/MLP curve topology while its raw operator
recentres within 1.5 vox using logit probability plus normalized CT contrast.
On s5, the radius 2 matched-below raw prefix improves same-chain continuity
by 9.76%; the matched-below clean prefix improves it by 2.75%.
Radius 3 on those same prefixes has lower coverage; its clean continuity
also decreases. The original publication froze the method before the first s1
coverage/connectivity evaluation; the completed postprocessor holdout appears
below. Added-flow / ownership / native-augmentation results remain in the [separate side study](overlap-ownership-study.md).

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

## FP32 predictor input reproduction

The measured input is the four-channel float32 side output before native uint8
rounding. Quantized native-u8 variant evaluations: 0.
[The input-reproduction card](float-input-reproduction.md) supplies pinned model
and source identities, exact normalization/window blending, the 74-line
[float-export patch](native-predict-float.patch), a standard-library
[application utility](apply_native_float_patch.py), and the model/export command.
These publish the already-measured adapter; method parameters remain unchanged.

## Run the published generation and small checks

[`logit_maps.py`](logit_maps.py) supplies both score maps.
[`bounded_logit_recenter.py`](bounded_logit_recenter.py) exposes the complete
fixed-topology raw generation primitive and CLI. The default mode is the
frozen `ct-energy-control`; `--mode probability-only` runs its causal control.
Unchanged upstream native cleanup is the required delivery stage after this
raw operator; raw deployment is stopped by the heldout switch-count result below.

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

## First s1 postprocessor parameter holdout

The method and operating-point protocol were frozen on s5. The immutable
[freeze commit `f88e889`](https://github.com/blucca/fiber-continuity/tree/f88e8894fa7dad1a56f670796f893a6793618faa)
was pushed at **2026-11-09 23:23:21 UTC**, and its public source acceptance
completed at **23:24:25 UTC**. The first s1 reference evaluation began at
**23:24:48 UTC** and completed at **23:28:04 UTC**. Heldout case evaluations: 1;
postprocessor parameter tuning on s1: 0. The selected primary remained
`ct-energy-control`; the probability-only mode remained its causal control.
The pretrained model's plans report 18 training cases; original case membership
remains a separate provenance field. This is a postprocessor parameter holdout.

The s1 cube has the same 7.91 µm lattice and its original manual graph.
Visible manual arc is 25,213.810 vox and the visible-reference continuity
ceiling is 0.9937939376. Radius 2 is primary; radius 3 uses the same radius 2
matched prefixes. Known sustained support, unknown/unannotated arc and
ambiguous-between-trees arc each retain their exact metric field below.

### Complete s1 outputs

| Mode / stage / bracket | Curves | Radius | C | Continuity | Interior / boundary switches | Known sustained arc (vox) | Unknown arc (vox) | Ambiguous arc (vox) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline / raw | 330 | 2 | 0.536871 | 0.278677 | 3 / 0 | 10541.497 | 10088.046 | 1050.062 |
| baseline / raw | 330 | 3 | 0.714958 | 0.476316 | 4 / 0 | 14218.709 | 6494.021 | 1180.819 |
| probability-only / raw | 330 | 2 | 0.539110 | 0.292110 | 4 / 0 | 10507.356 | 10257.124 | 1041.817 |
| probability-only / raw | 330 | 3 | 0.710087 | 0.467454 | 6 / 0 | 14088.181 | 6759.504 | 1162.053 |
| ct-energy-control / raw | 330 | 2 | 0.540039 | 0.293184 | 4 / 0 | 10438.591 | 10284.917 | 1073.241 |
| ct-energy-control / raw | 330 | 3 | 0.711934 | 0.469980 | 6 / 0 | 14153.116 | 6752.363 | 1189.640 |
| baseline / clean | 75 | 2 | 0.404060 | 0.230280 | 3 / 0 | 8119.264 | 5383.728 | 828.990 |
| baseline / clean | 75 | 3 | 0.528714 | 0.405083 | 3 / 0 | 10748.175 | 2791.189 | 916.081 |
| probability-only / clean | 76 | 2 | 0.408031 | 0.238897 | 4 / 0 | 8132.526 | 5542.873 | 813.610 |
| probability-only / clean | 76 | 3 | 0.529312 | 0.402731 | 4 / 0 | 10747.709 | 2976.621 | 894.974 |
| ct-energy-control / clean | 77 | 2 | 0.410613 | 0.245712 | 3 / 0 | 8141.998 | 5583.282 | 824.389 |
| ct-energy-control / clean | 77 | 3 | 0.534965 | 0.408036 | 3 / 0 | 10887.326 | 2937.673 | 908.551 |

The full CT-clean output has 77 curves: r2 C 0.410613 / continuity 0.245712,
versus the 75-curve mature clean baseline 0.404060 / 0.230280. Both have
3 interior / 0 boundary observed switches. At r3, full CT-clean gives
0.534965 / 0.408036 versus 0.528714 / 0.405083, again 3 / 0 versus 3 / 0.

**Raw deployment is stopped.** CT raw has 4 observed interior switches versus
baseline 3 at r2, and 6 versus 4 at r3. The probability-only raw control has
the same increased switch counts. Published raw generation is an intermediate
stage; unchanged native cleanup 45° / minimum 100 / black 16 is a required
part of the complete delivery recipe.

### Matched coverage: primary CT control

Whole-curve length-descending / stable-ID prefixes bracket pairwise common
manual coverage at radius 2, then the same prefix is measured at radius 3.
The mature baseline values remain those in the full-output table.

| Mode / stage / bracket | Curves | Radius | C | Continuity | Interior / boundary switches | Known sustained arc (vox) | Unknown arc (vox) | Ambiguous arc (vox) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CT / raw / below | 305 | 2 | 0.536664 | 0.293061 | 4 / 0 | 10429.636 | 10122.352 | 1069.013 |
| CT / raw / below | 305 | 3 | 0.707347 | 0.469857 | 6 / 0 | 14089.368 | 6615.281 | 1182.495 |
| CT / raw / above | 306 | 2 | 0.537088 | 0.293061 | 4 / 0 | 10429.636 | 10126.220 | 1069.013 |
| CT / raw / above | 306 | 3 | 0.707925 | 0.469857 | 6 / 0 | 14099.466 | 6615.281 | 1182.495 |
| CT / clean / below | 74 | 2 | 0.403873 | 0.239840 | 3 / 0 | 8000.031 | 5444.603 | 824.389 |
| CT / clean / below | 74 | 3 | 0.524463 | 0.398665 | 3 / 0 | 10638.092 | 2884.594 | 908.551 |
| CT / clean / above | 75 | 2 | 0.404926 | 0.240611 | 3 / 0 | 8019.039 | 5519.145 | 824.389 |
| CT / clean / above | 75 | 3 | 0.527234 | 0.400892 | 3 / 0 | 10704.916 | 2919.069 | 908.551 |

The clean 74-curve lower bracket gives **C 0.403873 / continuity 0.239840**
versus baseline **0.404060 / 0.230280**, a **4.15%** continuity increase.
The 75-curve upper bracket gives **0.404926 / 0.240611** (+4.49%).
Observed counts remain 3 interior / 0 boundary for candidate and baseline.
Together with the s5 clean lower-bracket gain of 2.75%, these results support
a clean-stage radius 2 continuous-arc increment across the two measured volumes.
Observed error-count reduction is 0.

**Radius 3 sensitivity:** the same 74/75 clean prefixes give continuity
0.398665 / 0.400892 versus baseline 0.405083. Their coverages
0.524463 / 0.527234 are lower than 0.528714. The positive matched-clean
increment is confined to the primary radius 2 scope; the radius 3 matched-clean
continuity change is negative.

### Probability-only causal control

| Mode / stage / bracket | Curves | Radius | C | Continuity | Interior / boundary switches | Known sustained arc (vox) | Unknown arc (vox) | Ambiguous arc (vox) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P-only / raw / below | 309 | 2 | 0.536482 | 0.291840 | 4 / 0 | 10488.764 | 10123.936 | 1037.590 |
| P-only / raw / below | 309 | 3 | 0.706057 | 0.467067 | 6 / 0 | 14042.534 | 6648.894 | 1154.908 |
| P-only / raw / above | 310 | 2 | 0.536983 | 0.291840 | 4 / 0 | 10498.401 | 10123.936 | 1037.590 |
| P-only / raw / above | 310 | 3 | 0.706636 | 0.467067 | 6 / 0 | 14052.171 | 6648.894 | 1154.908 |
| P-only / clean / below | 73 | 2 | 0.401018 | 0.235176 | 4 / 0 | 7980.208 | 5408.404 | 813.610 |
| P-only / clean / below | 73 | 3 | 0.518975 | 0.393484 | 4 / 0 | 10498.629 | 2920.895 | 894.974 |
| P-only / clean / above | 74 | 2 | 0.404605 | 0.237115 | 4 / 0 | 8067.504 | 5423.477 | 813.610 |
| P-only / clean / above | 74 | 3 | 0.522942 | 0.397451 | 4 / 0 | 10593.276 | 2928.617 | 894.974 |

Its full and matched clean outputs retain 4 interior switches versus baseline 3;
its control role and the frozen CT primary remain explicit.

### Which clean events changed

A read-only review of the saved baseline-clean, CT-clean and matched-clean
metric/prediction JSON mapped each event to its original raw source curve.
At both radii, the baseline and CT totals are 3 interior / 0 boundary, with
**2 shared tree-ID pairs, 1 baseline-only pair and 1 CT-only pair**. The two
shared events retain their source lineage; the baseline-only and CT-only
events occur on different original sources. The 74/75 matched CT prefixes
contain the same three event pairs as full CT-clean. The event composition
changes while its total remains 3 / 3. This review performs 0 new metric calls,
0 geometry generation and 0 parameter selection. Published event information
is aggregate; real geometry and event anchors remain in research caches.

### State-field separation for clean outputs

`known_tree` includes short known runs; `sustained_known_tree` includes runs
meeting the fixed 8-vox support threshold. Unknown and ambiguous states remain
separate from both:

| Clean output | Radius | Known arc incl. short (vox) | Sustained known arc (vox) | Short known support (vox) | Unknown arc (vox) | Ambiguous arc (vox) |
|---|---:|---:|---:|---:|---:|---:|
| baseline full | 2 | 8370.379 | 8119.264 | 251.115 | 5383.728 | 828.990 |
| CT full | 2 | 8522.787 | 8141.998 | 380.788 | 5583.282 | 824.389 |
| CT below | 2 | 8359.153 | 8000.031 | 359.123 | 5444.603 | 824.389 |
| CT above | 2 | 8385.910 | 8019.039 | 366.871 | 5519.145 | 824.389 |
| baseline full | 3 | 10875.827 | 10748.175 | 127.652 | 2791.189 | 916.081 |
| CT full | 3 | 11084.235 | 10887.326 | 196.909 | 2937.673 | 908.551 |
| CT below | 3 | 10835.001 | 10638.092 | 196.909 | 2884.594 | 908.551 |
| CT above | 3 | 10901.825 | 10704.916 | 196.909 | 2919.069 | 908.551 |

The reported gain is annotated same-chain continuity. Observed switch counts
use known sustained support; the tables preserve the accompanying unknown
and ambiguous arc and the connection-event totals. Method superiority, external adoption and awards each
remain 0. Surface fitting, flattening and VC3D rendering remain subsequent
native-consumer checkpoints.
