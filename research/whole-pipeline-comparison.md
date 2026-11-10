# Whole-pipeline comparison at matched manual coverage

**For the fixed same-coverage long-chain objective, use the complete legacy
spline/gap pipeline with center-path DP and native cleanup. For maximum
full-output coverage in these cubes, use the current author's raw AFV.**
The two operating points answer different downstream questions.

The full legacy DP pipeline passes the frozen radius-2 continuity gate against
both the current default raw AFV and an equally native-cleaned companion on
two previously scored cubes. Its lower/upper gains against current raw are
**+21.961% / +19.547% in s1** and **+8.229% / +6.868% in s5**. The older pipeline
without DP also passes. All 18,502 native-clean segments in the four legacy
outputs pass the current author's unchanged assigned-family validator.

This is an end-to-end benchmark on **two already revealed cases**. The original
[first spatial parameter-heldout validation](continuous-path-spatial-validation.md)
retains its earlier source, time and comparator. New blind cases, model runs,
geometry generation and parameter searches in this benchmark: **0**.
The [direct DP transfer onto current AFV geometry](current-medial-ridge-transfer.md)
retains its failed gates and 17 invalid native segments. That default migration
stays stopped.

## Frozen sources, frame and protocol

- Benchmark plan frozen **2026-11-10 08:29:40 UTC**; source/input checkpoint
  **08:33:35 UTC**, before the new benchmark measurements; completed
  **08:37:36 UTC**.
- Legacy pipeline and native cleanup:
  [ScrollPrize/villa@c3d9da6](https://github.com/ScrollPrize/villa/tree/c3d9da6fe42c3bb46fd2603ca060845d843296c3).
  The baseline is its mature spline/catalog/gap-MLP output after cleanup.
- Fixed DP:
  [fiber-continuity@1afa30ab](https://github.com/blucca/fiber-continuity/tree/1afa30ab840f7606f0b6594213731c5a88202c61).
  The candidate is that same legacy raw pipeline, fixed center-path DP,
  then the original cleanup.
- Current emitter:
  [Qualzz/AVF_SPLINE_GENERATOR@bee798f7](https://github.com/Qualzz/AVF_SPLINE_GENERATOR/tree/bee798f72751169065fe020d4ad02c52519c2d2b),
  all algorithm defaults, with CPU threads capped at 2. `current_raw` is its
  actual default output. `current_clean` applies the same 45-degree joins,
  100-voxel minimum length and 16-voxel exterior-black cleanup as the legacy
  outputs.
- Shared segmentation input:
  [scrollprize/fiber_hz_vt@0905e68](https://huggingface.co/scrollprize/fiber_hz_vt/tree/0905e68f14b33d1b98fd32d726f2c97607dea80c).
  CT is uint8 ZYX; original four-channel probabilities are FP32 CZYX.
  Current native V/H input uses
  `(rint(255 * P[family]) + .5 * rint(255 * P[intersection])) / 255`.
  The author's recommended V2 model has its own input identity and zero runs here.
- Original manual graph references, ROI-local XYZ at **7.91 micrometers per
  voxel**, shape ZYX `(256,256,256)`. Cases are
  `s1_08997_02997_02497_256` and `s5_07997_02997_05497_256`; their XYZ origins
  are `[2497,2997,8997]` and `[5497,2997,7997]`.
- Evaluator and matcher:
  [fiber-continuity@8c90536](https://github.com/blucca/fiber-continuity/tree/8c90536373bc98e09689e042074e017a1afd5364),
  unchanged measured sources. Higher-coverage output curves are ordered longest-first,
  then by string ID; binary search finds whole-curve lower/upper brackets
  around the poorer output's radius-2 manual coverage. Radius 3 uses the
  identical prefixes. Both brackets are reported with their coverage residuals.

Passing requires positive radius-2 same-chain continuity changes in both
brackets on both cases, with observed interior/boundary switches held or
reduced at radii 2 and 3. Raw and clean comparator gates are independent;
the legacy-baseline architecture control is also displayed independently.
The [complete JSON](whole-pipeline-results.json) includes all 32 matched rows,
16 unique full-output rows, search measurements, retained counts/lengths,
supported/unknown/ambiguous arcs, eligible chains, runtime and native audit.

## Operating contracts and architecture control

| Candidate / comparator | Case | Radius-2 continuity change, lower / upper | Radius-2 observed interior switches, candidate / comparator | Radius-3 change on the same prefixes, lower / upper | Gate |
|---|---|---:|---:|---:|---|
| DP-clean / current raw | s1 | +21.961% / +19.547% | 1 / 2 | +5.567% / +3.287% | pass |
| DP-clean / current raw | s5 | +8.229% / +6.868% | 0 / 1 | +10.549% / +8.177% | pass |
| DP-clean / current clean | s1 | +22.979% / +20.525% | 1 / 2 | +6.503% / +4.184% | pass |
| DP-clean / current clean | s5 | +8.504% / +7.137% | 0 / 1 | +11.646% / +9.210% | pass |
| Legacy baseline-clean / current raw | s1 | +17.049% / +14.699% | 1 / 2 | +5.769% / +4.307% | pass |
| Legacy baseline-clean / current raw | s5 | +5.211% / +3.043% | 0 / 1 | +15.782% / +13.341% | pass |
| Legacy baseline-clean / current clean | s1 | +16.859% / +15.664% | 1 / 2 | +6.729% / +5.241% | pass |
| Legacy baseline-clean / current clean | s5 | +5.485% / +3.305% | 0 / 1 | +16.956% / +14.466% | pass |

The legacy architecture contributes a substantial part of the cross-pipeline
advantage. DP-specific gains come from the earlier independently frozen
comparison with that legacy baseline: fresh radius-2 native-clean gains of
**+5.581% / +5.581% in s1** and **+0.939% / +3.029% in s5**, with observed
switches held. Its s5 radius-3 continuity decreases. Each comparison keeps
its own common-coverage denominator and original source/time.

The current raw emitter produces greater full-output coverage and greater
absolute full-output continuity in both cubes:

| Case | Full output | Radius-2 coverage | Radius-2 same-chain continuity | Observed interior / boundary switches |
|---|---|---:|---:|---:|
| s1 | Legacy DP-clean | 38.343% | 0.173168 | 1 / 0 |
| s1 | Current raw | 54.303% | 0.230708 | 3 / 0 |
| s5 | Legacy DP-clean | 40.303% | 0.218433 | 0 / 0 |
| s5 | Current raw | 52.919% | 0.276338 | 2 / 0 |

Manual references are partial. Observed switches apply to sustained known-tree
support; unknown and ambiguous arcs keep their own totals. Radius-3 sensitivity
uses the radius-2 prefixes, so coverage residuals change: DP/current-raw s1
is −1.254 / −1.981 percentage points, while s5 is +4.627 / +3.436 points.
Surface-fit quality, whole-volume behavior and operator adoption have their
own downstream measurements.

## Reproduce with the existing commands

Start with the source-pinned mature raw envelopes and shared CT/probabilities
from the [baseline provenance](../README.md#real-aggregate-baseline-s5-threshold-60)
and [FP32 export reproduction](float-input-reproduction.md). Generate the fixed
legacy DP output using the [existing command](continuous-centre-path-study.md#execute-the-measured-geometry),
then apply [`native/clean_traces.py`](../native/clean_traces.py) with the original
villa pin. The [current-emitter command](current-medial-ridge-transfer.md#repeat-the-fixed-comparison)
produces the default AFV; import it with [`afv_to_traces.py`](../afv_to_traces.py).
Use the same CT and cleanup for the current-clean companion and legacy control.

For each case, compare the complete legacy-clean candidate against the current
raw output:

```bash
python match_coverage.py --reference data/reference.json \
  --baseline data/current-raw-traces.json --dp data/legacy-dp-clean.json \
  --case s1_08997_02997_02497_256 --output results/whole-pipeline-raw.json
```

Repeat with `current-clean-traces.json`, then with `legacy-baseline-clean.json`
as the candidate. The command returns full metrics and both matched brackets
at radii 2 and 3, including the exact retained prefixes for local inspection.

The assigned-family audit uses the unchanged current-author
`tracing.valid_segments`, `Predictions` and `NativeSampler` with
`q=(ROI-local native XYZ-.5)/2`, maximum tracing step `.25` voxels and tolerance
`1e-4`. Both pooled and native uint8 fields must retain assigned-family
dominance. Every original adjacent segment is tested, including adjacency
on curves with declared gaps; all IDs, points and gap ranges stay intact.
The [executable audit snippet](current-medial-ridge-transfer.md#native-family-contract-audit)
and the previously measured 27,031-segment current-raw positive control retain
their original scope. Geometry integration and the statistical gate have
separate rows.

For native downstream consumers, the existing
[clean envelope → V4 → typed ObjectStore/frame bridge](../native/README.md#from-a-measured-trace-envelope)
passed all 79 legacy DP-clean s1 curves and 5,168 points with one origin
application. The fresh typed check is independent of this aggregate benchmark.

## Complete 32 matched rows

|candidate|comparator|case|r|bracket|normalized geometry / count|Δcoverage pp|Δcontinuity %|candidate I/B|comparator I/B|
|---|---|---|---:|---|---|---:|---:|---:|---:|
|old_dp_clean|current_raw|s1_08997_02997_02497_256|2|below|current_raw/59|+0.40829|+21.96116|1/0|2/0|
|old_dp_clean|current_raw|s1_08997_02997_02497_256|3|below|current_raw/59|-1.25360|+5.56666|2/0|5/0|
|old_dp_clean|current_raw|s1_08997_02997_02497_256|2|above|current_raw/60|-0.22932|+19.54731|1/0|2/0|
|old_dp_clean|current_raw|s1_08997_02997_02497_256|3|above|current_raw/60|-1.98113|+3.28735|2/0|5/0|
|old_dp_clean|current_clean|s1_08997_02997_02497_256|2|below|current_clean/59|+0.45350|+22.97878|1/0|2/0|
|old_dp_clean|current_clean|s1_08997_02997_02497_256|3|below|current_clean/59|-1.22997|+6.50328|2/0|5/0|
|old_dp_clean|current_clean|s1_08997_02997_02497_256|2|above|current_clean/60|-0.18411|+20.52488|1/0|2/0|
|old_dp_clean|current_clean|s1_08997_02997_02497_256|3|above|current_clean/60|-1.95750|+4.18379|2/0|5/0|
|old_baseline_clean|current_raw|s1_08997_02997_02497_256|2|below|current_raw/57|+0.15958|+17.04880|1/0|2/0|
|old_baseline_clean|current_raw|s1_08997_02997_02497_256|3|below|current_raw/57|+0.07675|+5.76888|2/0|5/0|
|old_baseline_clean|current_raw|s1_08997_02997_02497_256|2|above|current_raw/58|-0.22566|+14.69920|1/0|2/0|
|old_baseline_clean|current_raw|s1_08997_02997_02497_256|3|above|current_raw/58|-0.44791|+4.30705|2/0|5/0|
|old_baseline_clean|current_clean|s1_08997_02997_02497_256|2|below|current_clean/57|+0.20113|+16.85853|1/0|2/0|
|old_baseline_clean|current_clean|s1_08997_02997_02497_256|3|below|current_clean/57|+0.10038|+6.72904|2/0|5/0|
|old_baseline_clean|current_clean|s1_08997_02997_02497_256|2|above|current_clean/58|-0.18022|+15.66421|1/0|2/0|
|old_baseline_clean|current_clean|s1_08997_02997_02497_256|3|above|current_clean/58|-0.42427|+5.24074|2/0|5/0|
|old_dp_clean|current_raw|s5_07997_02997_05497_256|2|below|current_raw/43|+0.82226|+8.22870|0/0|1/0|
|old_dp_clean|current_raw|s5_07997_02997_05497_256|3|below|current_raw/43|+4.62651|+10.54940|1/0|3/0|
|old_dp_clean|current_raw|s5_07997_02997_05497_256|2|above|current_raw/44|-0.01493|+6.86810|0/0|1/0|
|old_dp_clean|current_raw|s5_07997_02997_05497_256|3|above|current_raw/44|+3.43568|+8.17705|1/0|3/0|
|old_dp_clean|current_clean|s5_07997_02997_05497_256|2|below|current_clean/43|+0.75429|+8.50405|0/0|1/0|
|old_dp_clean|current_clean|s5_07997_02997_05497_256|3|below|current_clean/43|+4.60874|+11.64623|1/0|3/0|
|old_dp_clean|current_clean|s5_07997_02997_05497_256|2|above|current_clean/44|-0.08290|+7.13656|0/0|1/0|
|old_dp_clean|current_clean|s5_07997_02997_05497_256|3|above|current_clean/44|+3.41221|+9.21019|1/0|3/0|
|old_baseline_clean|current_raw|s5_07997_02997_05497_256|2|below|current_raw/42|+0.60876|+5.21135|0/0|1/0|
|old_baseline_clean|current_raw|s5_07997_02997_05497_256|3|below|current_raw/42|+5.51170|+15.78230|1/0|3/0|
|old_baseline_clean|current_raw|s5_07997_02997_05497_256|2|above|current_raw/43|-0.24172|+3.04254|0/0|1/0|
|old_baseline_clean|current_raw|s5_07997_02997_05497_256|3|above|current_raw/43|+4.34646|+13.34122|1/0|3/0|
|old_baseline_clean|current_clean|s5_07997_02997_05497_256|2|below|current_clean/42|+0.54079|+5.48467|0/0|1/0|
|old_baseline_clean|current_clean|s5_07997_02997_05497_256|3|below|current_clean/42|+5.49954|+16.95604|1/0|3/0|
|old_baseline_clean|current_clean|s5_07997_02997_05497_256|2|above|current_clean/43|-0.30969|+3.30469|0/0|1/0|
|old_baseline_clean|current_clean|s5_07997_02997_05497_256|3|above|current_clean/43|+4.32869|+14.46575|1/0|3/0|

## Complete 16 full unique rows

|case|geometry|r|curves/points/gapped|coverage %|continuity|I/B|supported/unknown/ambiguous vox|eligible/count|
|---|---|---:|---|---:|---:|---:|---|---|
|s1_08997_02997_02497_256|old_dp_clean|2|79/5168/8|38.34345|0.17316769|1/0|8700.82327/5343.50565/13.46422|73/79|
|s1_08997_02997_02497_256|old_dp_clean|3|79/5168/8|51.05735|0.34803309|2/0|11710.98018/2546.40528/91.47047|73/79|
|s1_08997_02997_02497_256|current_raw|2|225/15963/0|54.30272|0.23070782|3/0|12256.03860/12160.17946/44.58902|125/225|
|s1_08997_02997_02497_256|current_raw|3|225/15963/0|74.10288|0.46872018|6/0|16967.61562/7811.69901/154.23559|130/225|
|s1_08997_02997_02497_256|current_clean|2|101/6150/0|49.88258|0.21621957|3/0|11272.83268/8371.97856/26.77669|93/101|
|s1_08997_02997_02497_256|current_clean|3|101/6150/0|67.92080|0.44286135|6/0|15648.43658/4405.20815/126.27914|94/101|
|s1_08997_02997_02497_256|old_baseline_clean|2|78/4379/8|37.29432|0.16151998|1/0|8492.47953/5426.53132/16.30947|72/78|
|s1_08997_02997_02497_256|old_baseline_clean|3|78/4379/8|51.21369|0.34087334|2/0|11696.41932/2398.12033/101.66929|72/78|
|s5_07997_02997_05497_256|old_dp_clean|2|67/5078/11|40.30310|0.21843346|0/0|6708.16424/5945.35481/0.00000|59/67|
|s5_07997_02997_05497_256|old_dp_clean|3|67/5078/11|56.74403|0.40253640|1/0|9559.19437/3187.31152/2.78818|61/67|
|s5_07997_02997_05497_256|current_raw|2|138/11431/0|52.91922|0.27633780|2/0|8796.91642/9001.56394/17.63633|84/138|
|s5_07997_02997_05497_256|current_raw|3|138/11431/0|73.98485|0.49743001|5/0|12404.65837/5507.62250/29.47637|92/138|
|s5_07997_02997_05497_256|current_clean|2|72/4604/0|49.15887|0.25942484|2/0|8202.13468/7060.65156/8.96072|63/72|
|s5_07997_02997_05497_256|current_clean|3|72/4604/0|67.22584|0.46820331|4/0|11297.80910/4073.19219/11.63367|64/72|
|s5_07997_02997_05497_256|old_baseline_clean|2|66/4167/11|39.23912|0.20796645|0/0|6526.89557/5940.84904/0.00000|59/66|
|s5_07997_02997_05497_256|old_baseline_clean|3|66/4167/11|56.46398|0.41270207|1/0|9482.08044/3087.43194/4.56810|60/66|

## Separate unchanged-author native family audit

All original adjacent segments audited at q=(native XYZ−.5)/2, including segments on gapped curves; original IDs/points/gaps all preserved. The previously completed current-raw AFV positive control has 27,031 valid segments; its original audit is linked above.

|case|candidate|curves/points/gapped|invalid segments/segments|invalid curves|invalid length/total native vox|hard contract|
|---|---|---|---|---:|---|---|
|s1_08997_02997_02497_256|old_dp_clean|79/5168/8|0/5089|0|0.00000/14476.64292|PASS|
|s1_08997_02997_02497_256|old_baseline_clean|78/4379/8|0/4301|0|0.00000/14331.46943|PASS|
|s5_07997_02997_05497_256|old_dp_clean|67/5078/11|0/5011|0|0.00000/12828.55399|PASS|
|s5_07997_02997_05497_256|old_baseline_clean|66/4167/11|0/4101|0|0.00000/12644.45415|PASS|


Code and hand-authored synthetic examples are MIT. Acquire raw CT/NML from the
[official Vesuvius data server](https://dl.ash2txt.org/datasets/fiber-skeletons/)
under its data license. This report publishes aggregate statistics; local
reproduction keeps real curves, reference geometry and selected prefixes in
local data directories. Original annotations and upstream models/methods are
credited to their authors.
