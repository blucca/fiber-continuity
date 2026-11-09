# Overlap ownership and native continuations

Two completed s5 experiments test the overlap-selection bottleneck identified
in the [earlier matched-coverage checkpoint](incoming-direction-study.md#matched-coverage-checkpoint).
Both lose same-chain continuity at the radius 2 matched-coverage bracket.
The retained main method is [bounded logit-plus-CT recentering](bounded-logit-study.md);
ownership, added-flow and native-augmentation runs remain experimental side studies.

## Shared measurement scope

Development data: the original s5 256³ cube at 7.91 µm; manual visible arc
15,654.564 vox. Radius 2 is primary, radius 3 is a fixed sensitivity analysis.
Observed switches refer to sustained known manual-tree support (runs ≥8 vox),
with interior and boundary events separated. Unknown/unannotated arc is counted
independently. Every aggregate row in this note has 0 interior / 0 boundary
switches. The s1 coverage/connectivity evaluation count at this publication
freeze is 0; s1 is reserved for the frozen main method.

The fixed segmentation model is
[`scrollprize/fiber_hz_vt@0905e68f14b33d1b98fd32d726f2c97607dea80c`](https://huggingface.co/scrollprize/fiber_hz_vt/tree/0905e68f14b33d1b98fd32d726f2c97607dea80c).
The mature threshold 60 spline/catalog/gap-MLP/cleanup baseline uses
[the pinned villa source](https://github.com/ScrollPrize/villa/tree/c3d9da6fe42c3bb46fd2603ca060845d843296c3).
Its extended-clean result is 56 curves: r2 coverage / continuity
**0.278677 / 0.160557**, sustained known arc 4,041.766 vox and unknown arc
6,958.827 vox; r3 **0.418161 / 0.276466**, known 6,257.501 and unknown
4,887.625 vox. The pretrained model's training membership and new-method
parameter holdout remain separate provenance fields.

## What the native single-block contract does

[Catalog._compare_pair](https://github.com/ScrollPrize/villa/blob/c3d9da6fe42c3bb46fd2603ca060845d843296c3/vesuvius/src/vesuvius/fiber_spline_generator/extend/catalog.py#L227-L282) checks family first. Direct duplicate
suppression and suffix/head overlap reconciliation are enabled for sources
from different block job IDs. Sources from one extractor/add_block result
retain independent identities at that stage; geometrically admissible gaps
can still connect inside one block.

[Strict containment](https://github.com/ScrollPrize/villa/blob/c3d9da6fe42c3bb46fd2603ca060845d843296c3/vesuvius/src/vesuvius/fiber_spline_generator/extend/catalog.py#L85-L111) tests complete short-curve support:
median distance ≤0.20 vox, p90 ≤0.40, max ≤0.65, projected span ≥97%,
endpoint tangent angle ≤8°, and monotonic correspondence. Its aliases require
[a direct retained representative](https://github.com/ScrollPrize/villa/blob/c3d9da6fe42c3bb46fd2603ca060845d843296c3/vesuvius/src/vesuvius/fiber_spline_generator/extend/catalog.py#L284-L305), with length-descending,
stable-ID order. The wider [`overlap.compare` duplicate descriptor](https://github.com/ScrollPrize/villa/blob/c3d9da6fe42c3bb46fd2603ca060845d843296c3/vesuvius/src/vesuvius/fiber_spline_generator/extend/overlap.py#L117-L182)
stops contained continuation search; Catalog accepts only `kind=overlap` from
that descriptor path. Alias suppression has its separate strict gate.

Explicit [`Stitcher.expand()`](https://github.com/ScrollPrize/villa/blob/c3d9da6fe42c3bb46fd2603ca060845d843296c3/vesuvius/src/vesuvius/fiber_spline_generator/extend/stitch.py#L99-L143) adds
[continuation overlap proposals](https://github.com/ScrollPrize/villa/blob/c3d9da6fe42c3bb46fd2603ca060845d843296c3/vesuvius/src/vesuvius/fiber_spline_generator/extend/continuation.py#L18-L90) for catalog chains,
including chains from the same block. The native accepted overlap trims shared
intervals and joins at an interior seam. Learned gap joins add inferred bridges.
[`covered()`](https://github.com/ScrollPrize/villa/blob/c3d9da6fe42c3bb46fd2603ca060845d843296c3/vesuvius/src/vesuvius/fiber_spline_generator/extend/continuation.py#L102-L123) filters redundant endpoint alternatives;
source geometry remains archived. Catalog ingestion, whole-curve selection and
actual native overlap/gap expansion are distinct stages.

## Whole-curve geometric novelty

[`overlap_priority.py`](overlap_priority.py) ranks predicted polylines by greedy
marginal aligned geometric arc. It subdivides original segments to at most
2 vox, keeps their exact arc weights, and tests midpoint-to-segment distances
within 1.5 vox. Candidates compete within the same family with absolute tangent
cosine ≥ cos(15°); the tangent chord spans 8 vox of predicted geometry. Ties use
marginal arc, total length, source kind and stable ID.

The ranking is an experimental geometric selection proxy. Original curve
objects, IDs, points, gaps and point order stay intact in the full ranked
archive. A consumer selects whole-curve prefixes or a marginal-arc cutoff;
this ranking creates 0 cross-curve connections. Manual geometry is opened only
by the independent evaluator after geometry selection is complete.

The completed single-block clean pool contains 105 curves. Direct strict
containment removes 0; the ranked archive retains all 105. A declared
100-vox marginal-arc cutoff selects 61. Reference-based matched-coverage
bracketing normalizes the comparison after the geometry-only ranking:

| Ownership selection | Curves | Radius | Manual coverage | Same-chain continuity | Sustained known arc (vox) | Unknown arc (vox) |
|---|---:|---:|---:|---:|---:|---:|
| ranked archive | 105 | 2 | 0.355475 | 0.187249 | 7757.204 | 12260.386 |
| marginal arc ≥100 | 61 | 2 | 0.319689 | 0.161550 | 4686.858 | 7764.582 |
| ownership below | 48 | 2 | 0.277713 | 0.137491 | 4052.808 | 6830.665 |
| ownership below | 48 | 3 | 0.404635 | 0.256420 | 5931.309 | 4942.026 |
| ownership above | 49 | 2 | 0.282582 | 0.139115 | 4129.356 | 6905.703 |
| ownership above | 49 | 3 | 0.411911 | 0.260401 | 6042.101 | 4982.821 |

The 48/49 prefixes bracket the r2 baseline coverage, with continuity
0.137491 / 0.139115 versus 0.160557. **Matched-coverage ownership selection
fails to improve continuity.** Radius 3 measures those same r2-selected
prefixes; both coverage and continuity are lower there.

## Reverse gate: emitted-walk purity and original-arc budget

The added 105 curves passed the fixed endpoint emitted-reverse arc-agreement
gate described by [`agreement()` / `reverse_consistent()`](incoming_tangent_probe.py).
For each endpoint, the query weights are lengths of the reverse walk's emitted
segments; the target is the original curve. Distance ≤1.5 vox, absolute
cosine ≥0.94 and matched emitted reverse arc fraction ≥0.9 define that pass.

Whole-original revalidation uses original segments as queries and needs its
own covered-arc field. Saved reverse lengths give a separate arc-budget audit:
72 of the 105 passes have at least one reverse/original length ratio below 0.9.
After accounting for the fixed inward 8-vox input history, 26/105 still have
at least one reverse/(original−8) ratio below 0.9. Among the 47 original curves
at least 100 vox long, that history-adjusted count is 14/47. These ratios track
reverse path budget; original covered-segment fractions require reverse
geometry or saved correspondence.

A hand-authored synthetic 100-vox line with two 20-vox endpoint retraces passes
the existing purity gate with fractions 1 / 1. Swapping query/target to weight the
original line yields 0.22 / 0.22. The denominator changes the contract. The
reported native augmentation therefore uses **endpoint emitted-reverse
arc-agreement-pass 105**, with the original-arc budget scope above. Whole-curve
reverse coverage remains a separate verification field.

## Complete native augmentation

This run keeps the mature threshold 60 extracted polylines unchanged at input
and adds those 105 emitted-reverse purity passes before the native catalog /
Expander stage. It uses the same gap MLP, CT availability checks and default
cleanup 45° / minimum 100 / black 16 as the mature baseline. Native expansion
accepted **11 overlap links and 5 gap links**; its final clean output contains
94 curves. These operations create native continuations, distinct from the
whole-curve ranking's zero-join contract.

| Native output | Curves | Radius | Manual coverage | Same-chain continuity | Sustained known arc (vox) | Unknown arc (vox) |
|---|---:|---:|---:|---:|---:|---:|
| full native expanded-clean | 94 | 2 | 0.323405 | 0.176643 | 6590.528 | 11591.053 |
| full native expanded-clean | 94 | 3 | 0.476196 | 0.309301 | 10162.377 | 8151.407 |
| native matched below | 62 | 2 | 0.271939 | 0.141363 | 5225.099 | 8942.669 |
| native matched below | 62 | 3 | 0.399405 | 0.253761 | 8151.486 | 6181.356 |
| native matched above | 63 | 2 | 0.278812 | 0.147931 | 5326.277 | 8992.342 |
| native matched above | 63 | 3 | 0.408551 | 0.262907 | 8288.982 | 6197.539 |

Full r2 output has coverage / continuity 0.323405 / 0.176643. At the matched
upper bracket, 63 curves give **0.278812 / 0.147931** versus baseline
**0.278677 / 0.160557**: continuity decreases by 0.012626. The 62-curve lower
bracket also loses continuity. Radius 3 on both prefixes has lower coverage
and continuity. **Complete native augmentation fails the matched-coverage
continuity comparison.** Further overlap/gap threshold expansion is stopped.

## Run the small checks

```bash
python -m pip install numpy scipy
python research/check-ownership.py
```

The checks cover reversed near-duplicates, independent geometry, family
separation, transverse crossings, empty input, zero-length original edges,
exact arc weights and original object identity. This publication ships code,
hand-authored synthetic checks, aggregate measurements and pinned-source links.
Data/annotation attribution and licensing follow the main README. Real CT,
reference graphs and predicted geometry remain in research caches.

Main-method validation proceeds from the separate bounded-logit freeze.
Method superiority, external adoption and awards have each recorded 0 at
this side-study checkpoint.
