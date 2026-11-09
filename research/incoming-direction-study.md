# Keeping centres while extending fibers

A completed s5 development experiment combines the pinned mature spline/gap-MLP
pipeline with bounded transverse CT recentering and independently reverse-consistent
incoming-tangent traces. The fixed model and original manual graph remain shared
across controls. The evaluator uses the original 7.91 µm local XYZ frame.

## What the mechanism measurements changed

Across 11,778.815 vox of manual arc with complete transverse context, the
sigma1 CT minus sigma2 transverse background is positive on 91.919% of the arc,
with mean contrast 7.712 gray levels. Selecting the strongest CT peak point by
point pulls existing geometry toward neighbouring ridges. In the stable baseline
profile subset, radius1.5 CT-plus-shift-prior selection changes radius2 point
support from 69.474% to 67.481%; probability-peak selection gives 70.771%.

Keeping original curve topology, limiting displacement to 1.5 vox, smoothing it
along the original arc with sigma2 vox, projecting it perpendicular to the
8-vox incoming tangent and pinning endpoints changes the full result. On the
fixed stitched input, CT recentering gives radius2 coverage 0.394379 versus
0.380210 for the probability-only control. Both retain zero observed switches.
The raw continuity values are 0.191950 and 0.192546, respectively.

Open-loop log-probability tracing also loses geometry. Its accepted steps have
median probability 0.998276; 82.30% exceed 0.99. A 0.99→0.999 probability change
contributes only 0.00905 log-probability energy, below the 0.03125 half-voxel shift
prior. The fixed logit-energy control recovers more uninterrupted arc, while one
observed tree-ID switch remains. A reference-free reverse-flow gate retains
105 of its 177 curves and gives zero observed switches at radius2 and radius3.

## Complete development recipe

1. Reuse the pinned mature threshold60 spline/catalog/gap-MLP output.
2. Recenter its existing curves in a radius1.5 transverse disk: CT_G1 minus an
   additional transverse Gaussian-sigma2 background, local MAD normalization,
   log(Pfamily+full intersection), gate0.5 and shift prior r²/8. Apply the fixed
   arc smoothing, normal projection and endpoint pinning above.
3. Independently trace from the fixed original spline midpoints with incoming
   support8, step2, lookahead4, transverse search1.5, logit(Pfamily+fullI) clipped
   to [1e-5,1-1e-5], competing-ridge margin0.15 and finite radius8 context.
4. Retain whole new curves when each reverse walk agrees along ≥90% of its arc
   within distance1.5 and cosine0.94. Add those connected curves as independent
   constraints. Near-identical candidate filtering uses distance0.25/cosine0.99/
   arc95%; it removes zero candidates in this development run. Cross-curve
   connection creation in the augmentation step is zero.
5. Apply the same upstream cleanup45°/minimum100/black16 and shared evaluator.

The complete candidate set has 429 raw curves and 105 default-clean curves.
The original manual arc denominator is 15,654.564 vox; radius2 is primary and
radius3 is the fixed sensitivity measurement. Every row below has zero observed
interior/boundary switches on sustained annotated support.

| Radius | Stage | Mature MLP coverage / continuity | Complete augmentation coverage / continuity |
|---:|---|---:|---:|
|2|raw|0.381040 / 0.195376|0.432067 / 0.220094|
|2|default clean|0.278677 / 0.160557|0.355475 / 0.187249|
|3|raw|0.564750 / 0.336138|0.602619 / 0.358217|
|3|default clean|0.418161 / 0.276466|0.494383 / 0.313735|

At radius2, default-clean augmentation has 7,757.204 sustained-supported vox,
12,260.386 unknown/unannotated vox and 83 eligible chains. The baseline has
4,041.766 / 6,958.827 vox and 44 eligible chains. These full-output rows compare
both additional geometry and additional coverage. Whole-curve longest-first
matched-coverage brackets are the next comparison checkpoint. s1 remains
reserved for the complete frozen method.

The completed recipe/control/evaluation run takes 46.265 s on two CPU cores,
peak RSS462.715 MiB. Passing the clean geometry through the pinned native
Stitcher/catalog succeeds: 105 inputs, 105 canonical curves, matching radius2
coverage/continuity and zero observed switches. Atlas/spiral surface-fit delivery
is the subsequent native-consumer checkpoint.

## Try the reusable primitives

[`transverse_centering.py`](transverse_centering.py) exposes reference-free
CT/probability transverse score maps and bounded centre selection.
[`incoming_tangent_probe.py`](incoming_tangent_probe.py) exposes `trace()` and
`reverse_consistent()` on fixed CT uint8 ZYX and probability float32 CZYX4 arrays
(background, V, H, intersection). Curves use ROI-local XYZ and family V/H.
The module's default tracing energy is the measured probability-logit control.
The recipe uses the original mature geometry and the new gated curves together.

```bash
python -m pip install numpy scipy
python research/check-incoming.py
```

The code is experimental MIT research code. Original data/model/source and
attribution follow the main README. Only aggregate measurements and original
code are published here; the original CT, annotations and predicted geometry
remain in research caches. Manual annotations supply evaluation and diagnosis;
score generation and reverse filtering receive predictions and CT/probability
arrays. The pretrained model's training membership remains a separate property
from the new tracer's s5/s1 parameter-selection protocol.
