# Manual-NML evaluator contract v1

Measured source SHA-256:
`e46cb2dd5579231fefe8b33fd4173393496fdc10ad29e6525b7de39d06fbb010`.

## Original graph and coordinate frame

Reference JSON is an original WEBKNOSSOS NML instance graph:

- `format`: `WebKnossos NML`.
- `filename_origin_zyx`: the supplied global XYZ ROI origin in reverse order.
- `roi_size`: cubic side length in voxels.
- `trees[*].attributes.id`: unique original manual tree ID.
- `trees[*].nodes[*]`: original node `id`, global `xyz`, ROI-local `xyz_local`,
  `inside_roi`; converter also retains original node `attributes`.
- `trees[*].edges[*]`: original `source`, `target`, `inside_roi`.
- Original counts, graph maximum degrees and connected-component sizes are
  checked by `prepare_reference`.

The converter preserves NML `parameters` and `groups`. Its `frame` includes
the supplied ROI origin/shape, original scale/unit and Full Cube bounding boxes.
Global XYZ = local XYZ + origin XYZ. Geometry uses XYZ voxel coordinates;
CT/probability arrays use ZYX/CZYX. The canonical manual cases use isotropic
7.91 µm spacing and NML offset `[0,0,0]`. Coordinate translations use the
supplied ROI origin in that original frame. New-scan affine resampling belongs
to its explicitly declared input frame.

`edge.inside_roi` marks both original endpoints inside `[0,size)`³. The
evaluator additionally clips every original edge against the ROI box to retain
its visible arc. Original undirected edges are partitioned exactly once into
maximal nonbranch paths: degree ≠2 nodes are path endpoints. Degree-3 branches
keep their common manual tree ID. Zero-geometric-length edges retain graph
topology and contribute zero arc weight. Annotator tree names and prediction
family names are descriptive; geometric searches use all original tree IDs.

## Prediction inputs

JSON is a curve list or an envelope containing `curves`:

```json
{
  "coordinates":"ROI-local XYZ voxels",
  "shape_zyx":[64,64,64],
  "curves":[{"id":"synthetic","family":"V","points_xyz":[[8,10,12],[48,10,12]]}]
}
```

`id` is unique within a file. Complete `points_xyz` represents one connected
polyline, including all bridges. Splitting a chain creates separate IDs.
Optional `gaps` ranges are retained as declared gap metadata; their geometry
is evaluated through the complete point chain. Envelopes may carry `case`,
`coordinates`, `shape_zyx`, `frame` and method provenance. Declared frame/case
fields are checked against the reference. Global input uses explicit
`--prediction-coordinates global-xyz`. NPZ uses M×3 `points_xyz`, K+1 `offsets`
(start 0, end M, nondecreasing), optional length-K `chain_ids` and `family`;
loading uses `allow_pickle=False`.

## Fixed parameters

Primary: radius **2 vox** (15.82 µm), different-tree ambiguity margin **1 vox**,
minimum sustained support **8 vox**, resampling step **≤1 vox**, ROI boundary
band **2 vox**. Sensitivity: radius **3 vox** (23.73 µm) with all other parameters
fixed. Polylines are clipped and resampled with actual segment lengths as
weights. Spatial hashing retrieves candidates; distances use exact
point-to-segment projection. Integration is length-weighted midpoint quadrature.

## Three jointly interpreted measurements

### Manual length coverage

For clipped manual subsegment j with midpoint q_j and length w_j:

```text
C = sum(w_j * [distance(q_j, predicted ROI segments) <= radius]) / sum(w_j)
```

The denominator includes positive visible arc from boundary-crossing original
edges. Reports separate fully-inside original edges, boundary-intersecting
original edges, ROI boundary band, interior and original outside arc.

### Sustained observed tree-ID switches

Each predicted-chain subsegment is classified:

1. Outside the ROI: `outside_roi`.
2. Nearest manual distance d1 > radius: `unknown_unannotated`.
3. Nearest different-tree distance d2 has d2−d1 < 1 vox:
   `ambiguous_between_trees`.
4. Otherwise: `known_tree` using the nearest original tree ID.

A contiguous known-tree run with length ≥8 vox is sustained support. Adjacent
sustained runs in chain order with different tree IDs create a switch event.
A→unknown→B retains the intervening unknown arc and yields one event when both
known runs meet the support threshold. A→unknown→A preserves identity. Shorter
known runs have their own `short_known_support` total.

An event is `boundary_cross_tree` when its two 8-vox support windows or the
intervening connection touch the 2-vox boundary band/outside ROI; other events
are `interior_cross_tree`. Each event includes the two IDs, support lengths,
arc positions, XYZ anchors, original edge node IDs and prediction edge indices.

**Observation scope:** sustained original-tree changes on the available manual
annotations. Unknown, ambiguous and outside arcs have separate totals.
Each eligible chain has at least one sustained run. Switch rates per 1000 vox
use actual sustained support; zero-support denominators yield JSON `null`.

### Same-chain continuity

For each original maximal nonbranch manual path, find all predicted chain IDs
within radius at each sampled midpoint. Sum the longest contiguous hit run of
one predicted chain on each manual path; divide by total manual ROI arc.
Re-entry after an original path's outside-ROI interval starts a new run.

- Raw continuity: `path_length_weighted_same_chain_continuity`.
- Visible-reference ceiling: sum of each path's longest visible manual run
  divided by the total manual ROI arc.
- Normalized continuity: raw numerator divided by that visible-reference
  ceiling numerator (`same_chain_continuity_of_visible_reference_ceiling`).
- Best-single-chain total coverage and per-path fragmentation are also reported.

The synthetic complete line and its two-fragment prediction both have C=1
and zero observed switches; their raw continuity values are 1 and 0.55 under
the fixed 2-vox endpoint tolerance.

## Comparison and output

Compare methods at matched manual C, then use interior switch counts and
same-chain continuity. Keep boundary switches, eligible counts, sustained,
unknown and ambiguous arc alongside those columns. Freeze development
parameters before examining the cross-scroll tracer-heldout cube. Pretrained
model training membership is a separate provenance field.

`evaluate.py --summarize` checks and summarizes the reference graph. Measured
outputs include input SHA-256 and supplied provenance. `--provenance FILE`
copies that JSON into the result; adjacent `reference.nml.source.json` is also
retained when present. Those locally supplied records stay in local results.
The CLI and programmatic `evaluate(reference, curves, Parameters())` share
the same mathematics. Native VC3D training replay is a separate protocol with
execution count 0 here.
