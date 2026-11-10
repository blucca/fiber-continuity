# Current medial-ridge AFV: fixed-center-path transfer

**Keep the author's default AFV geometry at this operating point.** The frozen
center-path DP fails the transfer gate on both measured cubes. Applying the
same native cleanup to both methods also fails. The original positive result
against the older spline/gap pipeline remains a separate source-pinned study.

This comparison uses two **already inspected** cubes, the existing fixed
`scrollprize/fiber_hz_vt` predictions and the original manual graphs. New blind
tests, model runs and parameter searches: 0.

## Exact comparator and inputs

- Current emitter: [`Qualzz/AVF_SPLINE_GENERATOR@bee798f72751169065fe020d4ad02c52519c2d2b`](https://github.com/Qualzz/AVF_SPLINE_GENERATOR/tree/bee798f72751169065fe020d4ad02c52519c2d2b).
  All algorithm options use its defaults; CPU threads are capped at 2.
  This is the medial-ridge/structure-tensor emitter with family-locked tracing
  and the author's final segment validator.
- Fixed prediction source: `scrollprize/fiber_hz_vt@0905e68f14b33d1b98fd32d726f2c97607dea80c`.
  Input channels are the previously measured native V/H plus half-intersection:
  `VH[i] = (rint(255 * P[i+1]) + 0.5 * rint(255 * P[3])) / 255`.
  The shared float32 array has shape `(2,256,256,256)`; the emitter applies its
  own quantization and 2× pooled tracing grid. The recommended V2 segmentation
  model has its own input identity and has zero runs in this study.
- Center path: the unchanged [`1afa30ab` freeze](https://github.com/blucca/fiber-continuity/tree/1afa30ab840f7606f0b6594213731c5a88202c61),
  including the same stations, energy, 29 states, radius 1.5, smoothing and
  same-station pointwise control. Existing curve IDs, gaps and topology stay
  intact. The raw AFV is the author's actual operating point.
- Companion cleanup: the original native 45° joins, 100-voxel minimum length
  and 16-voxel CT-exterior distance, applied equally to both outputs.
- Native frame: XYZ, original 7.91 µm voxels; CT/prediction arrays are ZYX.
  The AFV contains ROI-local L0 coordinates in this run. Its writer maps
  tracing coordinates as `native = 2 * tracing + 0.5`.

The two cases are `s1_08997_02997_02497_256` and
`s5_07997_02997_05497_256`. Default AFV outputs contain 225 / 138 curves and
15,963 / 11,431 points. Equal native cleanup retains 101 / 72 curves.

## Complete matched-coverage result

Longest-first whole-curve prefixes bracket the poorer output's radius-2 manual
coverage. Both brackets count. Radius 3 reuses those exact retained prefixes.
Passing requires a positive continuity gain in both radius-2 brackets and
observed interior/boundary switches held or reduced at both radii, in both
cases. Raw and clean gates are evaluated separately.

| Case | Stage | Radius-2 continuity gain, lower / upper | Coverage difference pp, lower / upper | Radius-3 observed interior switches, baseline → DP | Gate |
|---|---|---:|---:|---:|---|
| s1 | author raw | −2.110% / −2.145% | +0.0924 / −0.0021 | 6 → 10 / 6 → 10 | failed |
| s5 | author raw | −10.692% / −10.729% | +0.0188 / −0.0041 | 5 → 5 / 5 → 5 | failed |
| s1 | same native clean | +1.676% / −0.222% | +0.3939 / −0.0038 | 6 → 10 / 6 → 10 | failed |
| s5 | same native clean | −7.700% / −8.518% | +0.0796 / −0.2221 | 4 → 4 / 4 → 4 | failed |

Radius-2 observed interior switches remain 3 / 3 in s1 and 2 / 2 in s5;
boundary switches are 0 in every full/matched row. Radius-3 continuity gains
are −1.508% in raw s1, −5.560% / −5.572% in raw s5,
+1.633% / +0.563% in clean s1, and −3.847% / −4.449% in clean s5.

[All 24 full rows, all 16 matched rows, frozen parameters and complete audit](current-medial-ridge-results.json)
retain coverage, continuity, sustained support, unknown/ambiguous arc,
eligible chains, exact retained counts and the pointwise control. The original
manual references are partial: supported tree identity, unknown arc and
between-tree ambiguity are reported separately.

## Native family-contract audit

After the complete statistical run, the author's **unchanged**
`tracing.valid_segments` checks every segment at at most 0.25 tracing-voxel
spacing. Assigned-family dominance must hold in both the author's pooled
uint8 field and its native uint8 trilinear sampler, with tolerance `1e-4`.
This is an integration check; the original statistical gate stays fixed.

| Case | Geometry | Invalid fibers / total | Invalid segments / total | Invalid native arc (voxels) |
|---|---|---:|---:|---:|
| s1 | original author AFV | 0 / 225 | 0 / 15,738 | 0 |
| s1 | same-station pointwise | 6 / 225 | 11 / 15,738 | 17.878 |
| s1 | fixed DP | 5 / 225 | 14 / 15,738 | 22.795 |
| s5 | original author AFV | 0 / 138 | 0 / 11,293 | 0 |
| s5 | same-station pointwise | 1 / 138 | 1 / 11,293 | 1.602 |
| s5 | fixed DP | 2 / 138 | 3 / 11,293 | 4.910 |

The original AFV is the positive frame/sampler control: all **27,031** segments
pass. The reader matches every ID, gap list and binary64 point in all 363
fibers exactly. The center-path objective preserves topology but its moved
segments violate the emitter's locked-family contract in 7 fibers. The native
family audit and manual tree-switch measurements have distinct definitions
and separate rows.

## Evaluate an AFV directly

The new [`afv_to_traces.py`](../afv_to_traces.py) reads the author's binary64
SQLite AFV schema without changing point positions. It retains one shared
endpoint between successive 256-segment blocks and exposes the original
metadata in a standard trace envelope.

```bash
# ROI-local AFV: origin is zero. For full-volume AFV, pass the NML ROI's XYZ origin.
python afv_to_traces.py --afv data/default.afv --case s1_08997_02997_02497_256 \
  --origin-xyz 0 0 0 --output data/default-traces.json
python evaluate.py --reference data/reference.json --traces data/default-traces.json \
  --case s1_08997_02997_02497_256 --radius 2 --output results/default-r2.json
```

`python check.py --examples temp/synthetic` also writes and verifies a
hand-built 601-point, three-block AFV fixture, including binary64 overlap,
origin handling and source ID. The native dataset/archive parity check above
uses the actual author-generated files.

## Repeat the fixed comparison

Start with the same `(4,Z,Y,X)` background/V/H/intersection float32 model
array and uint8 CT cube. Prepare exactly the measured shared input:

```python
import numpy as np
p = np.load("data/probabilities-czyx-f32.npy", mmap_mode="r")
vh = np.lib.format.open_memmap("data/shared-vh.npy", mode="w+", dtype="f4",
                             shape=(2,) + p.shape[1:])
for i in (0, 1):
    vh[i] = (np.rint(p[i + 1] * 255) + 0.5 * np.rint(p[3] * 255)) / 255
vh.flush()
```

With the pinned emitter installed, its default command and the fixed
postprocessor are:

```bash
avf-spline-generator --predictions data/shared-vh.npy --voxel-size-um 7.91 \
  --threads 2 --output data/default.afv --work-dir data/author-work \
  --coordinate-space ROI-local:s1_08997_02997_02497_256
# Import default.afv with the preceding AFV command, then:
python research/run_centre_path.py --ct data/ct.npy \
  --probabilities data/probabilities-czyx-f32.npy \
  --traces data/default-traces.json --output results/centre-path
python match_coverage.py --reference data/reference.json --baseline data/default-traces.json \
  --dp results/centre-path/dp-raw.json --case s1_08997_02997_02497_256 \
  --output results/matched-raw.json
```

[`match_coverage.py`](../match_coverage.py) returns both original full outputs,
the actual lower/upper prefixes, and four matched rows. Its fixed r2
longest-first/binary-search procedure matches the measured run; r3 reuses the
same prefixes. Six synthetic evaluator/comparison checks include both rich
output directions and direct verification of the selected-prefix metrics.

For the clean companion, use the existing
[`native/clean_traces.py`](../native/clean_traces.py) on each raw envelope with
the same CT and pinned villa source, then supply the two clean envelopes to
the same matching command. The pointwise output from `run_centre_path.py`
provides the full-output causal control. Geometry generation, reference
evaluation and native family validation remain separate steps.

To repeat the native family check with the pinned emitter installed:

```python
import numpy as np
from afv_to_traces import read_afv
from avf_spline_generator.storage import Predictions, NativeSampler
from avf_spline_generator.tracing import valid_segments

curves = read_afv("data/default.afv", "same-ROI", origin=(0, 0, 0))["curves"]
tracing = np.load("data/author-work/tracing.npy", mmap_mode="r")
native = NativeSampler(Predictions("data/shared-vh.npy"), cache_mib=128)
invalid = sum(int((~valid_segments((np.asarray(c["points_xyz"]) - 0.5) / 2,
               tracing, {"V": 1, "H": 2}[c["family"]], native)).sum()) for c in curves)
print({"invalid_segments": invalid})  # original author AFV: 0 in both measured cases
```

Raw CT, original NMLs, predictions and derived real curves remain at their
original/private sources; this repository publishes code and aggregate
measurements. [The first source-pinned spline-pipeline validation](continuous-path-spatial-validation.md)
retains its original time, inputs, fresh-test scope and results. Default
center-path migration to the current emitter stops here; model changes,
additional thresholds and whole-volume rollout have zero new runs.
