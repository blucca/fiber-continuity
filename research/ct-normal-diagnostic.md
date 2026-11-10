# Keep the CT normal independent of the suspect fiber tangent

A local CT intensity normal supplies a useful extra signal for a tracer. At the
middle of one fixed benchmark transition, the existing fiber tangent departs
**28.165°** from the independently estimated CT tangent plane. Forcing the CT
normal into that fiber's perpendicular plane rotates the evidence axis by the
same angle. The observed intensity-peak count changes from **2 to 4** when the
original CT normal is retained.

**Keep the CT normal.** Derive an in-plane direction by projecting the fiber
*tangent* into its plane. An anchored correct-layer direction is the reference
for a later re-tracing task.

This is a native-CT companion to the [artificial contact/coverage probe](tracer-sheet-contact-probe.md).
It uses the original fixed `fiber_hz_vt` input and emitter
[`bee798f7`](https://github.com/Qualzz/AVF_SPLINE_GENERATOR/tree/bee798f72751169065fe020d4ad02c52519c2d2b),
from the [complete prospective pipeline benchmark](whole-pipeline-spatial-validation.md).
Actual V2 runner/model/frame, labelled sheet events and genuine branch controls
have their own material and evaluation gate.

## Fixed-event diagnostic

The original s5 full raw output has eight radius-2 sustained manual tree-ID
switches. We recovered the detailed support table with one unchanged evaluator
support-component call and took its **first interior event in original order**.
The three positions are the left support end minus 8 native voxels, the midpoint
of the unsupported transition, and the right support start plus 8 voxels.

Native CT is uint8, 7.91 µm per voxel. The gradient scale is 1 native voxel and
integration scale 3; each tensor has original 33×33×33 context. The strongest
CT gradient-tensor axis provides the intensity normal. Both profile controls
use the same positions, CT smoothing and peak thresholds. Intensity profiles
average over ±4 voxels in two in-plane directions. The control retains cached
CT normals and projects the tangent into their planes.

| Position | CT largest/middle eigenvalue | Fiber departure from CT tangent plane | Peaks, fiber-transverse frame | Peaks, CT-normal frame |
|---|---:|---:|---:|---:|
| Before | 12.156 | 2.583° | 3 | 3 |
| Middle | 7.141 | 28.165° | 2 | 4 |
| After | 4.193 | 7.000° | 3 | 2 |

The first display plane has 49 / 52 outside-ROI samples in the respective
controls, out of 4,225; those samples are masked. The middle and after planes
have all 4,225 samples inside the original CT. Tensor contexts and averaged
normal profiles are fully available at all three positions.

The normal is an **intensity orientation** and the peaks are intensity
candidates. Physical leaf/lamina labels and genuine-delamination controls in
this diagnostic each have count **0**. Carrier lineage follows anchored
branch correspondences; correct-sheet successor and genuine branch
preservation are the actual-task acceptance tests. Original geometry is
retained: **0 automatic repairs, 0 geometry edits**.

[Complete aggregate](ct-normal-diagnostic-results.json) includes both frame
controls and all boundary counts. The CT probe took 1.054 seconds; the cached
normal control took 0.684 seconds on one CPU. Published material contains
source, numerical controls and aggregates; upstream CT/NML access provides
the research input provenance.

## Runnable primitive

[`ct_normal_diagnostic.py`](ct_normal_diagnostic.py) accepts native CT in ZYX
array order and a native XYZ sampling position. Fixed scales match the study.
`ct_normal` returns a unit CT normal and the tensor eigenvalues when full
context and gradient energy are available. `sheet_frame` retains that normal
while creating an in-plane tangent/lateral frame. Flat CT, missing context and
vanishing in-plane direction have explicit `None` outcomes.

With NumPy and SciPy in your research environment:

```sh
python research/check-ct-normal.py
```

The small check covers native XYZ derivative order, flat/boundary CT context,
and an off-sheet tangent with the CT evidence axis retained. The actual event
and all three normal/eigenvalue outputs also have a source-port parity check.

To select a diagnostic on your own inputs, run the public evaluator on the
same-frame trace envelope and reference; its full JSON retains
`connectivity.events` and `connectivity.per_chain`. Use the original
`left_support_arc_end_vox` / `right_support_arc_start_vox` and curve ID to
sample a declared event. Keep CT intensity evidence, manual-ID support and
physical branch annotations as individually recorded outputs.
