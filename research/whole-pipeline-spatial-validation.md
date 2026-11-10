# Prospective whole-pipeline spatial validation

**Choose the original legacy spline/gap-MLP pipeline plus native cleanup
(`old_baseline_clean`) for the frozen matched-coverage long-chain objective in
these two prospective ROIs. Choose the current author's raw AFV for full-output
coverage and absolute same-chain continuity. Fixed DP default upgrade stops.**

The legacy baseline passes both current-raw and equally-cleaned architecture
gates. DP-clean's primary gate fails at the s1 radius-2 upper bracket
**−0.74768%**; its equally-cleaned companion gate passes. The DP-specific gate
fails in both cases: all four radius-2 brackets decrease. Native integration
passes independently for all **21,977** legacy-clean segments and **35,799**
segments in two new current-raw positive controls.

This study evaluates the same source-pinned complete legacy spline/gap pipeline,
fixed center-path DP and native cleanup against the current author's default
raw output and an equally native-cleaned companion. The primary, companion
and DP-specific gates are independent. The legacy architecture controls have
their own rows.

## Prospective selection and provenance

The [immutable public preregistration](https://raw.githubusercontent.com/blucca/fiber-continuity/bd4aac2b230094a898db52b8f1cbf12e9a6799e8/research/whole-pipeline-spatial-freeze.json)
was accepted at **2026-11-10 12:08:51.716738 UTC**, before the new manual-reference intake.
All methods, source pins, model input and the selection rule were fixed there.

| Role | Evaluated case | Selection |
|---|---|---|
| s1 native cube | `s1_00497_01497_03997_256` | Lexicographically first previously unscored native 256 cube |
| s5 deterministic crop | `s5_06622_02122_04122_256` | Centre `[128:384]^3` of lexicographically first native 512 source `s5_06494_01994_03994_512` |

Selection used original archive names. The s5 source Full Cube and the evaluated
256-cube crop use their declared separate origins; array axes are ZYX,
geometry is ROI-local XYZ and voxel spacing is 7.91 micrometers. Original
manual node/edge/tree IDs and branches are retained, and existing edge–ROI
clipping defines the evaluated reference arcs.

**Model-training provenance:** the fixed `fiber_hz_vt@0905e68` checkpoint names
`Dataset003_sk-fibers_hzvt-augmented-2`, declares an **18-item labeled dataset pool**,
and uses fold **0**, `3d_fullres` and `nnUNetTrainerMedialSurfaceRecall`.
The [fixed-model source registry](fixed-model-training-provenance.json) records
18 current input filenames in public `Dataset002_sk-fibers-hzvt-20250228` and
21 in public `Dataset003_sk-fibers-hzvt-20250404`. All fields of Dataset002's
published `dataset.json` match the checkpoint's published and embedded dataset metadata.
Both corpora list the source cubes for all eight evaluated ROIs: seven direct
cube names and the declared 512-cube parent of the s5 crop above. The original
checkpoint-linked augmented-item list, parent mapping and actual fold-0
train/validation split supply per-case model exposure; those records remain
pending. The recommended V2 model retains its separate input identity.

**Postprocessor/comparator provenance:** prospective scope covers the frozen
postprocessor/comparator parameters and first reference performance in these
two ROIs. The immutable freeze was accepted before manual-reference intake.
Corrected source/crop QA completed **12:46:54.055378 UTC**, paired fixed-input
checks **12:52:22.583165 UTC**, all geometry **13:04:41.992572 UTC**, and the
all-geometry/source-frame precheck **13:04:43.230199 UTC**. Reference performance
opened at **13:04:43.582135 UTC** for s1 and **13:07:00.217502 UTC** for s5.
These model-training and postprocessor/reference-order records are separate.

## Source-QA attempt and pre-prediction erratum

Attempt 1 stopped at the s5 source-input assertion at **2026-11-10 12:19:57 UTC**,
before predictions or manual-reference scores. The original all-inside-node
test checked 15,610 manual nodes; nearest-integer and floor sampling each
matched 15,609. The single unmatched node had degree 0 and no incident edge.
The official `voxelize_skeleton` writes binary labels along `tree.edges`.
The 15,609 inside edge-bearing nodes all matched their binary labels.

The [independent input-QA erratum](https://raw.githubusercontent.com/blucca/fiber-continuity/013082ece698896cc0bed77de7843b29e56cddd5/research/whole-pipeline-spatial-input-erratum.json)
records that source-generator semantics and defines the QA denominator as
inside edge-bearing manual nodes. The complete-hit requirement remains
**100%**. The original isolated node and every original node, edge, tree ID and
branch remain in the evaluation reference.

The erratum was accepted by immutable HTTP readback at
**2026-11-10 12:38:23.916100 UTC**, with prediction, geometry and reference
performance runs still **0**. Attempt 2 used the same complete-hit rule on
the original source frames and declared crop frames:

| ROI / source | QA frame | Inside edge-bearing nodes | Binary-label hits | Isolated inside nodes retained | Result |
|---|---|---:|---:|---:|---|
| `s1_00497_01497_03997_256` | source | 2713 | 2713 | 0 | PASS |
| `s1_00497_01497_03997_256` | crop | 2713 | 2713 | 0 | PASS |
| `s5_06494_01994_03994_512` | source | 15609 | 15609 | 1 | PASS |
| `s5_06622_02122_04122_256` | crop | 2243 | 2243 | 0 | PASS |

The same preregistered two cases, s5 centre crop, model, DP, current emitter,
cleanup and matcher continue after the QA correction. Attempt 1 remains a
recorded data-entry failure. This correction concerns source-mask eligibility;
prediction parameters and the manual graph remain frozen.

## Fixed methods and gate

- Legacy spline/catalog/gap-MLP and identical native cleanup: `ScrollPrize/villa@c3d9da6`.
- Fixed DP: `fiber-continuity@1afa30ab`.
- Current default emitter: `Qualzz/AVF_SPLINE_GENERATOR@bee798f7`.
- Fixed segmentation: `scrollprize/fiber_hz_vt@0905e68`.
- Unchanged evaluator/matcher: `fiber-continuity@8c90536`.
- Cleanup: 45-degree joins, 100-voxel minimum length, 16-voxel exterior-black distance.

The radius-2 matcher orders whole curves longest-first, then by string ID,
and reports both lower/upper brackets and residual manual coverage. Radius 3
uses the same selected prefixes. Each gate requires positive radius-2
same-chain continuity changes in both brackets on both new cases and
observed interior/boundary switches held or reduced at both radii.

| Gate | Candidate | Comparator | Actual result |
|---|---|---|---|
| Primary | `old_dp_clean` | `current_raw` | FAIL |
| Companion | `old_dp_clean` | `current_clean` | PASS |
| DP-specific | `old_dp_clean` | `old_baseline_clean` | FAIL |
| Architecture control | `old_baseline_clean` | `current_raw` | PASS |
| Architecture control | `old_baseline_clean` | `current_clean` | PASS |

## Complete operating points

| Candidate / comparator | ROI | R2 continuity change, lower / upper | R2 observed I/B, candidate : comparator | R3 change, same lower / upper prefixes | R3 observed I/B, candidate : comparator | Case gate |
|---|---|---:|---|---:|---|---|
| `old_dp_clean` / `current_raw` | s1 | +1.00588% / -0.74768% | 0/0 : 0/0 | +6.37404% / +2.71550% | 0/0 : 0/0 | FAIL |
| `old_dp_clean` / `current_raw` | s5 | +4.10436% / +2.81256% | 3/0 : 8/0 | +7.79380% / +6.04947% | 5/0 : 10/0 | PASS |
| `old_dp_clean` / `current_clean` | s1 | +3.01208% / +1.18880% | 0/0 : 0/0 | +6.40390% / +2.74335% | 0/0 : 0/0 | PASS |
| `old_dp_clean` / `current_clean` | s5 | +3.86900% / +2.58300% | 3/0 : 7/0 | +7.81735% / +6.07227% | 5/0 : 10/0 | PASS |
| `old_dp_clean` / `old_baseline_clean` | s1 | -2.20645% / -1.32129% | 0/0 : 0/0 | -3.60780% / -2.24525% | 0/0 : 0/0 | FAIL |
| `old_dp_clean` / `old_baseline_clean` | s5 | -2.71637% / -2.71637% | 3/0 : 3/0 | +1.71486% / +1.71486% | 5/0 : 5/0 | FAIL |
| `old_baseline_clean` / `current_raw` | s1 | +1.65282% / +0.17769% | 0/0 : 0/0 | +8.21852% / +6.49524% | 0/0 : 0/0 | PASS |
| `old_baseline_clean` / `current_raw` | s5 | +6.42627% / +6.06660% | 3/0 : 8/0 | +5.29237% / +4.20576% | 5/0 : 10/0 | PASS |
| `old_baseline_clean` / `current_clean` | s1 | +3.74954% / +2.18577% | 0/0 : 0/0 | +8.23362% / +6.50986% | 0/0 : 0/0 | PASS |
| `old_baseline_clean` / `current_clean` | s5 | +6.18864% / +5.84885% | 3/0 : 7/0 | +5.31500% / +4.22793% | 5/0 : 10/0 | PASS |

The original legacy baseline supplies the simpler passing matched-coverage
operating point. DP-specific radius-2 changes are **−2.20645% / −1.32129% in
s1** and **−2.71637% / −2.71637% in s5**. s1 radius-3 DP-specific changes also
decrease (**−3.60780% / −2.24525%**); s5 radius-3 changes increase
(**+1.71486% / +1.71486%**). Each pair retains its own common-coverage target,
whole-curve brackets and coverage residuals.

Current raw has the greatest full-output coverage and absolute continuity
among all four outputs in each case at both radii. Full-output radius-2
operating measurements are:

| ROI | Full output | Radius-2 coverage | Radius-2 same-chain continuity | Observed interior / boundary switches |
|---|---|---:|---:|---|
| s1 | `old_baseline_clean` | 31.75848% | 0.16422768 | 0 / 0 |
| s1 | `old_dp_clean` | 33.15787% | 0.16708045 | 0 / 0 |
| s1 | `current_raw` | 49.88953% | 0.24827759 | 1 / 0 |
| s1 | `current_clean` | 42.73332% | 0.21926087 | 1 / 0 |
| s5 | `old_baseline_clean` | 36.39092% | 0.19798412 | 3 / 0 |
| s5 | `old_dp_clean` | 36.11414% | 0.19126157 | 3 / 0 |
| s5 | `current_raw` | 48.26671% | 0.24945007 | 8 / 0 |
| s5 | `current_clean` | 44.22738% | 0.22780038 | 7 / 0 |

The [complete aggregate JSON](whole-pipeline-spatial-results.json) retains all
**40 matched rows and 16 unique full-output rows**, supported/unknown/ambiguous
arcs, eligible-chain counts, coverage residuals, both radii and every negative
result. Manual references are partial; observed switches apply to sustained
known-tree support. Full-output coverage and matched-coverage continuity are
separate operating measurements.

## Independent native integration

|case|candidate|curves/points/gapped|invalid segments/segments|invalid curves|invalid/total length native vox|hard contract|
|---|---|---|---|---:|---|---|
|s1_00497_01497_03997_256|old_dp_clean|65/5199/14|0/5134|0|0.00000/13757.50017|PASS|
|s1_00497_01497_03997_256|old_baseline_clean|65/4425/14|0/4360|0|0.00000/13709.32460|PASS|
|s5_06622_02122_04122_256|old_dp_clean|90/6874/14|0/6784|0|0.00000/18342.63660|PASS|
|s5_06622_02122_04122_256|old_baseline_clean|90/5789/14|0/5699|0|0.00000/18262.39873|PASS|
|s1_00497_01497_03997_256|current_raw|309/16922/0|0/16613|0|0.00000/26575.15461|PASS|
|s5_06622_02122_04122_256|current_raw|266/19452/0|0/19186|0|0.00000/30707.71725|PASS|

The unchanged current author's assigned-family validator evaluates every
original adjacent segment, including adjacency on curves with declared gaps.
Original IDs, order, points and gap annotations remain intact. Both native
uint8 and pooled tracing fields, maximum `.25`-voxel tracing step and `1e-4`
assigned-family tolerance retain the frozen contract. Integration and the
statistical gates are recorded independently.

## Reproduce and scope

Use the original two source NMLs and the evaluated ROI origins:

```bash
python nml_to_reference.py \
  --nml data/fibers_s1a_00497z_01497y_03997x_256_v00.nml \
  --origin-xyz 3997 1497 497 --size 256 --output data/s1/reference.json
python nml_to_reference.py \
  --nml data/fibers_s5_06494z_01994y_03994x_512_v03.nml \
  --origin-xyz 4122 2122 6622 --size 256 --output data/s5/reference.json
python match_coverage.py --reference data/s1/reference.json \
  --baseline data/s1/current-raw-traces.json \
  --dp data/s1/legacy-baseline-clean.json \
  --case s1_00497_01497_03997_256 --output results/spatial-s1-legacy-raw.json
```

Repeat the matcher with the s5 files and case `s5_06622_02122_04122_256`.
For s5 CT and labels, use the original 512 source's fixed ZYX `[128:384]^3`
crop; the evaluated XYZ origin is `[4122,2122,6622]`. The NML keeps the original
512 Full Cube and every original node/edge/tree ID. The existing converter
rebases local coordinates and inside flags; the evaluator measures original-edge
intersections with the declared 256 ROI.

Use the [existing full-pipeline commands](whole-pipeline-comparison.md#reproduce-with-the-existing-commands)
with the two cases and frame from the preregistration. The DP-specific pair
uses `legacy-baseline-clean.json` as the matcher baseline and
`legacy-dp-clean.json` as the candidate. All geometry is terminal before
opening the new manual-reference performance.

Source/input checks began at **2026-11-10 12:52:20.969872 UTC**. The complete
aggregate finished at **13:10:39.691239 UTC**; independent native audit
finished at **13:10:39.520143 UTC**. A concrete current-emitter import invocation
was repaired by restoring the original author's `PYTHONPATH`; already-complete
legacy and DP geometry stages were reused unchanged. Scientific source
changes and post-result model/parameter/crop searches remain **0**.

The default recommendation for this measured matched-coverage objective is
the original legacy pipeline with native cleanup. DP-clean/current-clean
retains its independent positive companion scope; DP default upgrade stops
under the primary and DP-specific gates. The current raw emitter supplies
the highest full-output coverage/absolute continuity in these two ROIs.

The [earlier two-case revealed benchmark](whole-pipeline-comparison.md),
[first DP-specific spatial validation](continuous-path-spatial-validation.md)
and [current-default-emitter DP transfer failure](current-medial-ridge-transfer.md)
retain their original source, comparator and time windows. The recommended V2
model remains a separate input identity. The present validation concerns
fixed-model postprocessing in these two spatial ROIs; surface quality,
whole-volume performance and operator adoption have their own measurements.

## Complete 40 matched rows

|candidate|comparator|case|r|bracket|normalized/count|delta coverage pp|delta continuity %|candidate I/B|comparator I/B|
|---|---|---|---:|---|---|---:|---:|---:|---:|
|old_dp_clean|current_raw|s1_00497_01497_03997_256|2|below|current_raw/49|+0.32198|+1.00588|0/0|0/0|
|old_dp_clean|current_raw|s1_00497_01497_03997_256|3|below|current_raw/49|+1.03911|+6.37404|0/0|0/0|
|old_dp_clean|current_raw|s1_00497_01497_03997_256|2|above|current_raw/50|-0.52897|-0.74768|0/0|0/0|
|old_dp_clean|current_raw|s1_00497_01497_03997_256|3|above|current_raw/50|-0.01483|+2.71550|0/0|0/0|
|old_dp_clean|current_clean|s1_00497_01497_03997_256|2|below|current_clean/49|+0.37455|+3.01208|0/0|0/0|
|old_dp_clean|current_clean|s1_00497_01497_03997_256|3|below|current_clean/49|+1.05697|+6.40390|0/0|0/0|
|old_dp_clean|current_clean|s1_00497_01497_03997_256|2|above|current_clean/50|-0.47210|+1.18880|0/0|0/0|
|old_dp_clean|current_clean|s1_00497_01497_03997_256|3|above|current_clean/50|+0.00303|+2.74335|0/0|0/0|
|old_baseline_clean|current_raw|s1_00497_01497_03997_256|2|below|current_raw/47|+0.01070|+1.65282|0/0|0/0|
|old_baseline_clean|current_raw|s1_00497_01497_03997_256|3|below|current_raw/47|+2.29667|+8.21852|0/0|0/0|
|old_baseline_clean|current_raw|s1_00497_01497_03997_256|2|above|current_raw/48|-0.65707|+0.17769|0/0|0/0|
|old_baseline_clean|current_raw|s1_00497_01497_03997_256|3|above|current_raw/48|+1.30816|+6.49524|0/0|0/0|
|old_baseline_clean|current_clean|s1_00497_01497_03997_256|2|below|current_clean/47|+0.06311|+3.74954|0/0|0/0|
|old_baseline_clean|current_clean|s1_00497_01497_03997_256|3|below|current_clean/47|+2.30553|+8.23362|0/0|0/0|
|old_baseline_clean|current_clean|s1_00497_01497_03997_256|2|above|current_clean/48|-0.60449|+2.18577|0/0|0/0|
|old_baseline_clean|current_clean|s1_00497_01497_03997_256|3|above|current_clean/48|+1.31702|+6.50986|0/0|0/0|
|old_dp_clean|old_baseline_clean|s1_00497_01497_03997_256|2|below|old_dp_clean/55|-0.14771|-2.20645|0/0|0/0|
|old_dp_clean|old_baseline_clean|s1_00497_01497_03997_256|3|below|old_dp_clean/55|-1.92669|-3.60780|0/0|0/0|
|old_dp_clean|old_baseline_clean|s1_00497_01497_03997_256|2|above|old_dp_clean/56|+0.12088|-1.32129|0/0|0/0|
|old_dp_clean|old_baseline_clean|s1_00497_01497_03997_256|3|above|old_dp_clean/56|-1.50313|-2.24525|0/0|0/0|
|old_dp_clean|current_raw|s5_06622_02122_04122_256|2|below|current_raw/73|+0.47770|+4.10436|3/0|8/0|
|old_dp_clean|current_raw|s5_06622_02122_04122_256|3|below|current_raw/73|-2.05961|+7.79380|5/0|10/0|
|old_dp_clean|current_raw|s5_06622_02122_04122_256|2|above|current_raw/74|-0.00574|+2.81256|3/0|8/0|
|old_dp_clean|current_raw|s5_06622_02122_04122_256|3|above|current_raw/74|-2.62957|+6.04947|5/0|10/0|
|old_dp_clean|current_clean|s5_06622_02122_04122_256|2|below|current_clean/73|+0.44523|+3.86900|3/0|7/0|
|old_dp_clean|current_clean|s5_06622_02122_04122_256|3|below|current_clean/73|-2.05946|+7.81735|5/0|10/0|
|old_dp_clean|current_clean|s5_06622_02122_04122_256|2|above|current_clean/74|-0.03821|+2.58300|3/0|7/0|
|old_dp_clean|current_clean|s5_06622_02122_04122_256|3|above|current_clean/74|-2.62942|+6.07227|5/0|10/0|
|old_baseline_clean|current_raw|s5_06622_02122_04122_256|2|below|current_raw/74|+0.27104|+6.42627|3/0|8/0|
|old_baseline_clean|current_raw|s5_06622_02122_04122_256|3|below|current_raw/74|-2.05262|+5.29237|5/0|10/0|
|old_baseline_clean|current_raw|s5_06622_02122_04122_256|2|above|current_raw/75|-0.17595|+6.06660|3/0|8/0|
|old_baseline_clean|current_raw|s5_06622_02122_04122_256|3|above|current_raw/75|-2.66548|+4.20576|5/0|10/0|
|old_baseline_clean|current_clean|s5_06622_02122_04122_256|2|below|current_clean/74|+0.23856|+6.18864|3/0|7/0|
|old_baseline_clean|current_clean|s5_06622_02122_04122_256|3|below|current_clean/74|-2.05246|+5.31500|5/0|10/0|
|old_baseline_clean|current_clean|s5_06622_02122_04122_256|2|above|current_clean/75|-0.20520|+5.84885|3/0|7/0|
|old_baseline_clean|current_clean|s5_06622_02122_04122_256|3|above|current_clean/75|-2.66533|+4.22793|5/0|10/0|
|old_dp_clean|old_baseline_clean|s5_06622_02122_04122_256|2|below|old_baseline_clean/85|+0.18403|-2.71637|3/0|3/0|
|old_dp_clean|old_baseline_clean|s5_06622_02122_04122_256|3|below|old_baseline_clean/85|+0.15673|+1.71486|5/0|5/0|
|old_dp_clean|old_baseline_clean|s5_06622_02122_04122_256|2|above|old_baseline_clean/86|-0.03500|-2.71637|3/0|3/0|
|old_dp_clean|old_baseline_clean|s5_06622_02122_04122_256|3|above|old_baseline_clean/86|-0.12735|+1.71486|5/0|5/0|

## Complete 16 full unique rows

|case|geometry|r|curves/points/gapped|coverage %|continuity|I/B|supported/unknown/ambiguous vox|eligible/count|
|---|---|---:|---|---:|---:|---:|---|---|
|s1_00497_01497_03997_256|old_dp_clean|2|65/5199/14|33.15787|0.16708045|0/0|6647.39795/6828.40192/0.00000|54/65|
|s1_00497_01497_03997_256|old_dp_clean|3|65/5199/14|47.31361|0.31476009|0/0|9644.00910/3992.69334/11.28355|56/65|
|s1_00497_01497_03997_256|current_raw|2|309/16922/0|49.88953|0.24827759|1/0|9747.18612/16153.86768/73.88738|117/309|
|s1_00497_01497_03997_256|current_raw|3|309/16922/0|70.70713|0.42526805|4/0|14121.76618/11979.51361/126.43074|135/309|
|s1_00497_01497_03997_256|current_clean|2|86/5739/0|42.73332|0.21926087|1/0|8471.46747/9448.04513/18.59518|72/86|
|s1_00497_01497_03997_256|current_clean|3|86/5739/0|59.57716|0.38928220|3/0|12046.07095/6091.44735/40.93337|74/86|
|s1_00497_01497_03997_256|old_baseline_clean|2|65/4425/14|31.75848|0.16422768|0/0|6325.96045/7092.31387/0.00000|54/65|
|s1_00497_01497_03997_256|old_baseline_clean|3|65/4425/14|46.84093|0.31085765|0/0|9528.73473/4058.29149/4.36535|56/65|
|s5_06622_02122_04122_256|old_dp_clean|2|90/6874/14|36.11414|0.19126157|3/0|10400.37294/7650.96897/45.22846|84/90|
|s5_06622_02122_04122_256|old_dp_clean|3|90/6874/14|49.60092|0.36112991|5/0|14196.70562/3870.31457/136.37083|86/90|
|s5_06622_02122_04122_256|current_raw|2|266/19452/0|48.26671|0.24945007|8/0|13668.10282/16472.42162/82.47182|138/266|
|s5_06622_02122_04122_256|current_raw|3|266/19452/0|69.89853|0.45546971|11/0|19727.02651/10502.40240/236.87960|151/266|
|s5_06622_02122_04122_256|current_clean|2|113/7312/0|44.22738|0.22780038|7/0|12618.93992/11509.06752/75.54736|103/113|
|s5_06622_02122_04122_256|current_clean|3|113/7312/0|63.84452|0.42342039|11/0|18094.95645/6088.99765/225.95779|106/113|
|s5_06622_02122_04122_256|old_baseline_clean|2|90/5789/14|36.39092|0.19798412|3/0|10385.37788/7504.00935/88.22500|82/90|
|s5_06622_02122_04122_256|old_baseline_clean|3|90/5789/14|50.17787|0.35855174|5/0|14262.92619/3724.25548/190.06111|86/90|

Code and hand-authored synthetic examples are MIT. Obtain real CT and manual
NML from the [official Vesuvius source](https://dl.ash2txt.org/datasets/fiber-skeletons/)
under its data license. This publication distributes aggregate statistics;
real curves, selected prefixes, event geometry and source CT/NML stay in
local reproduction directories. Original annotations, models and methods
are credited to their upstream authors.
