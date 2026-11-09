# Centerline-preserving tracing: first development measurements

The fixed-model benchmark isolates probability inference, centerline extraction,
and connection/cleanup. All measurements below use the same s5 256³ development
cube and the evaluator in this repository. s1 remains reserved for a frozen
tracer evaluation.

## Where recovered geometry is lost

The official nnU-Net TIFF reader returns the cached CT at the same ZYX indices;
Full Cube origin, XYZ/ZYX conversion and zero offset agree with the manual data.
The native whole-ROI z-score and nnU-Net z-score differ by at most 5.01×10⁻⁶.
The fixed model has 67.36% positive-voxel recall on the supplied binary manual
mask. Probability ≥0.5 exists within radius2/radius3 for 85.64%/88.68% of the
sampled manual arc, while the original V/H Lee skeleton before junction cutting
is within those radii for 40.04%/59.27%. Its median manual-arc distance is
2.385 vox. The saved spline median distance is 2.638 vox.

These are distinct measurements: positive-mask recall, nearby probability
support, voxel-skeleton proximity, and exact spline-segment arc coverage. The
manual mask/reference supplies an annotated subset; unknown predicted geometry
has its own denominator. The nearby probability corridors motivate preserving
multiple centerlines and incoming directions during tracing.

## One short-junction probe

[`junction-link-probe.py`](junction-link-probe.py) retains the fixed spline seeds
and scores cubic Hermite joins with incoming tangents and full family-plus-
intersection probability. Fixed settings: radius 12 vox, tangent support 8,
cosine≥0.94, probability tenth percentile≥0.65, reciprocal score margin≥0.10.
The function reads curves and probabilities; labels are reserved for evaluation.
The executable synthetic check needs NumPy and SciPy:

```bash
python -m pip install numpy scipy
python research/junction-link-probe.py
```

The real development run accepted 22 of 24 admitted candidate pairs. Whole run,
including four metric evaluations: 9.941 s on two CPU cores, peak RSS407.66 MiB.
Default cleanup remains the upstream 45°/100-vox/16-vox configuration.

| Radius | Output | Manual coverage | Same-chain continuity | Observed interior/boundary switches |
|---:|---|---:|---:|---:|
|2|MLP extended raw|0.381040|0.195376|0/0|
|2|short-junction raw|0.381292|0.196281|0/0|
|2|MLP extended-clean|0.278677|0.160557|0/0|
|2|short-junction clean|0.279895|0.157071|0/0|
|3|MLP extended raw|0.564750|0.336138|0/0|
|3|short-junction raw|0.564667|0.337344|0/0|
|3|MLP extended-clean|0.418161|0.276466|0/0|
|3|short-junction clean|0.420551|0.274951|0/0|

At radius2, short-junction raw output has 5437.077 sustained supported vox,
12,950.560 unknown vox and 89 eligible chains. Clean output has 4078.352 supported
vox, 6964.377 unknown vox and 44 eligible chains. At radius 3 the corresponding
raw/clean support is 8287.946/6307.022 vox and unknown 10291.553/4871.928 vox.
Observed switches apply to sustained annotated support; the unknown arcs remain
separate. This table covers one fixed development setting.

**Decision: stop expanding endpoint-only join parameters.** After default
cleanup, same-chain continuity is below the learned baseline at both radii;
coverage gains are 0.122/0.239 percentage points. The next experiment is
probability-conditioned centerline tracking inside the original CT, with
incoming-direction preservation, explicit competing paths and the shared
connection/coverage evaluator. Matched-coverage comparisons and frozen s1
validation are the next method checkpoints.

Code is MIT; original annotations and models follow the sources and licenses
in the main README. This report contains aggregate measurements and synthetic
code; real CT, NML and predicted geometry remain in local research caches.
