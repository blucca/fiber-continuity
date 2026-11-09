"""Logit-energy incoming-tangent tracing; same v1 seeds/geometry/control scope.

The CT transverse ridge is sigma1 CT minus a sigma2 transverse background,
in local MAD units. Original manual graphs are evaluation inputs only.
One development operating point is used; ROI-sized context bounds the walk.
"""
from dataclasses import asdict, dataclass
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class Parameters:
    probability_energy: str = "logitP clipped [1e-5,1-1e-5]"
    step_vox: float = 2.0
    lookahead_vox: float = 4.0
    tangent_support_vox: float = 8.0
    transverse_radius_vox: float = 1.5
    grid_step_vox: float = 0.5
    profile_radius_vox: float = 8.0
    ct_sigma_vox: float = 1.0
    transverse_background_sigma_vox: float = 2.0
    probability_floor: float = 0.5
    transverse_penalty: float = 0.125
    competition_margin: float = 0.15
    separated_peak_vox: float = 1.0
    max_arc_vox: float = 384.0
    min_arc_vox: float = 8.0
    dedup_radius_vox: float = 1.0
    dedup_tangent_cosine: float = 0.94
    dedup_fraction: float = 0.8

    def __post_init__(self):
        assert 0 < self.step_vox <= self.lookahead_vox <= self.tangent_support_vox
        assert 0 < self.grid_step_vox <= self.transverse_radius_vox
        assert self.profile_radius_vox >= (self.step_vox + self.lookahead_vox) / self.step_vox * self.transverse_radius_vox + self.transverse_background_sigma_vox
        assert 0 < self.probability_floor <= 1 and self.competition_margin >= 0
        assert self.max_arc_vox > self.min_arc_vox > 0


def arc(points):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def at_arc(points, s, query):
    return np.stack([np.interp(query, s, points[:, k]) for k in range(3)], axis=-1)


def unit(v):
    norm = float(np.linalg.norm(v))
    assert norm > 1e-10 and np.isfinite(norm)
    return v / norm


def frame(direction):
    u = unit(np.cross(direction, np.eye(3)[np.argmin(np.abs(direction))]))
    return u, np.cross(direction, u)


class Profiles:
    def __init__(self, ct, probabilities, parameters=Parameters()):
        assert ct.ndim == 3 and probabilities.shape == (4,) + ct.shape
        assert ct.dtype == np.uint8 and probabilities.dtype == np.float32
        self.p = parameters
        self.shape_xyz = np.array(ct.shape[::-1], dtype=float)
        self.ct1 = ndi.gaussian_filter(ct.astype(np.float32), parameters.ct_sigma_vox, mode="nearest")
        self.prob = probabilities
        axis = np.arange(-parameters.profile_radius_vox, parameters.profile_radius_vox + parameters.grid_step_vox / 2, parameters.grid_step_vox)
        uu, vv = np.meshgrid(axis, axis, indexing="ij")
        self.uv = np.stack([uu, vv], axis=-1)
        self.rr2 = uu*uu + vv*vv
        self.mad_mask = self.rr2 <= 36.
        self.mid = len(axis)//2
        self.offsets = self.uv[self.rr2 <= parameters.transverse_radius_vox**2 + 1e-8]
        self.offset_r2 = np.square(self.offsets).sum(1)
        # Disc neighbours define local maxima; distinct peaks encode competing paths.
        ds = np.linalg.norm(self.offsets[:, None] - self.offsets[None, :], axis=-1)
        self.neighbours = (ds <= parameters.grid_step_vox * 1.45) & (ds > 1e-8)

    def sample(self, field, xyz):
        shape = xyz.shape[:-1]
        coordinates = np.asarray(xyz[..., ::-1], np.float32).reshape(-1, 3).T
        return ndi.map_coordinates(field, coordinates, order=1, mode="constant", cval=np.nan, prefilter=False).reshape(shape)

    def probability(self, xyz, family):
        return self.sample(self.prob[1 if family == "V" else 2], xyz) + self.sample(self.prob[3], xyz)

    def energies(self, centres, direction, family, *, use_ct=False):
        u, v = frame(direction)
        xyz = (centres[:, None, None] + u[None, None, None]*self.uv[None, ..., :1]
               + v[None, None, None]*self.uv[None, ..., 1:])
        fp = self.probability(xyz, family)
        if use_ct:
            # Constant sampling above marks the finite ROI lattice. Only scores
            # with a complete transverse context enter the candidate path.
            ct = self.sample(self.ct1, xyz)
            complete = np.isfinite(ct).all((1, 2))
            bg = ndi.gaussian_filter(np.nan_to_num(ct, nan=0.), sigma=(0, self.p.transverse_background_sigma_vox/self.p.grid_step_vox, self.p.transverse_background_sigma_vox/self.p.grid_step_vox), mode="nearest", truncate=2.)
            dog = ct - bg
            centre = np.nanmedian(dog[:, self.mad_mask], axis=1)
            scale = np.maximum(1.4826*np.nanmedian(np.abs(dog[:, self.mad_mask]-centre[:, None]), axis=1), 1.)
            ridge = dog / scale[:, None, None]
        else:
            complete = np.isfinite(fp).all((1, 2))
            ridge = np.zeros_like(fp)
        clipped = np.clip(fp, 1e-5, 1.-1e-5)
        energy = np.log(clipped) - np.log1p(-clipped) + ridge
        energy = np.where((fp >= self.p.probability_floor) & complete[:, None, None] & np.isfinite(energy), energy, -np.inf)
        return energy, fp, ridge

    def next(self, point, direction, family, *, use_ct=False):
        p = self.p
        centres = point[None] + np.array([p.step_vox, p.step_vox+p.lookahead_vox])[:, None] * direction[None]
        if np.any(centres < p.profile_radius_vox) or np.any(centres > self.shape_xyz-1-p.profile_radius_vox):
            return None, {"stop": "roi_context_boundary"}
        energy, fp, ridge = self.energies(centres, direction, family, use_ct=use_ct)
        idx = np.rint(self.offsets / p.grid_step_vox).astype(int) + self.mid
        factor = (p.step_vox+p.lookahead_vox)/p.step_vox
        future_idx = np.rint(factor*self.offsets / p.grid_step_vox).astype(int) + self.mid
        score = .6*energy[0, idx[:, 0], idx[:, 1]] + .4*energy[1, future_idx[:, 0], future_idx[:, 1]] - p.transverse_penalty*self.offset_r2
        u, v = frame(direction)
        candidates = centres[0] + self.offsets[:, :1]*u + self.offsets[:, 1:]*v
        intermediate = point[None] + .5*(candidates-point[None])
        mid_probability = self.probability(intermediate, family)
        score[mid_probability < p.probability_floor] = -np.inf
        finite = np.isfinite(score)
        if not finite.any():
            return None, {"stop": "lost_corridor"}
        best = int(np.argmax(score - self.offset_r2*1e-8))
        competitor_scores = np.max(np.where(self.neighbours, score[None, :], -np.inf), axis=1)
        peaks = np.flatnonzero(finite & (score >= competitor_scores - 1e-9))
        distinct = [int(k) for k in peaks if np.linalg.norm(self.offsets[k]-self.offsets[best]) >= p.separated_peak_vox]
        runner = max((float(score[k]) for k in distinct), default=None)
        margin = float(score[best]-runner) if runner is not None else None
        details = {"score": float(score[best]), "probability": float(fp[0, idx[best, 0], idx[best, 1]]),
                   "lookahead_probability": float(fp[1, future_idx[best, 0], future_idx[best, 1]]),
                   "ridge_z": float(ridge[0, idx[best, 0], idx[best, 1]]),
                   "transverse_shift_vox": float(np.sqrt(self.offset_r2[best])),
                   "competing_peak_count": len(distinct), "margin": margin}
        if margin is not None and margin < p.competition_margin:
            return None, dict(details, stop="competing_ridges")
        return candidates[best], details


def front(fields, history, family, *, use_ct=False):
    p = fields.p
    history = np.asarray(history, float).tolist()
    output = [history[-1]]
    evidence, length = [], 0.
    for _ in range(int(np.ceil(p.max_arc_vox/p.step_vox))+1):
        h = np.asarray(history, float)
        s = arc(h)
        direction = unit(h[-1] - at_arc(h, s, max(0., s[-1]-p.tangent_support_vox)))
        point, details = fields.next(h[-1], direction, family, use_ct=use_ct)
        if point is None:
            return np.asarray(output), {"stop": details, "steps": evidence}
        step = float(np.linalg.norm(point-h[-1]))
        if length+step > p.max_arc_vox:
            return np.asarray(output), {"stop": {"stop": "arc_budget"}, "steps": evidence}
        output.append(point.tolist()); history.append(point.tolist()); evidence.append(details); length += step
        # A short incoming-history window is enough for the fixed tangent support.
        if len(history) > 12:
            history = history[-12:]
    raise AssertionError("positive step and arc budget should terminate the walk")


def point_directions(points):
    delta = np.gradient(points, axis=0)
    return delta / np.maximum(np.linalg.norm(delta, axis=1)[:, None], 1e-12)


def trace(curves, probabilities, ct, parameters=Parameters(), *, use_ct=False, progress=None):
    fields = Profiles(ct, probabilities, parameters)
    seed_rows = []
    for curve in curves:
        points = np.asarray(curve["points_xyz"], float)
        assert points.ndim == 2 and points.shape[1] == 3 and len(points) >= 2 and np.isfinite(points).all()
        assert curve["family"] in ("V", "H")
        s = arc(points)
        if s[-1] >= parameters.tangent_support_vox:
            seed_rows.append((float(s[-1]), str(curve["id"]), curve, points, s))
    seed_rows.sort(key=lambda row: (-row[0], row[1]))
    outputs, records = [], []
    accepted_cloud = {family: [] for family in ("V", "H")}
    accepted_directions = {family: [] for family in ("V", "H")}
    accepted_trees = {family: None for family in ("V", "H")}
    for number, (seed_length, seed_id, curve, points, s) in enumerate(seed_rows):
        family = curve["family"]
        middle = s[-1]/2
        seed = at_arc(points, s, middle)
        positions = np.linspace(max(0., middle-8.), min(s[-1], middle+8.), 9)
        source = at_arc(points, s, positions)
        tree = accepted_trees[family]
        if tree is not None:
            distance, near = tree.query(source)
            source_direction = point_directions(source)
            same = (distance <= parameters.dedup_radius_vox) & (np.abs(np.einsum("ij,ij->i", source_direction, accepted_directions[family][near])) >= parameters.dedup_tangent_cosine)
            if same.mean() >= parameters.dedup_fraction:
                records.append({"seed_id": seed_id, "status": "coincident_seed_filtered"})
                continue
        forward_history = at_arc(points, s, np.linspace(max(0., middle-parameters.tangent_support_vox), middle, 5))
        reverse_history = at_arc(points, s, np.linspace(min(s[-1], middle+parameters.tangent_support_vox), middle, 5))
        forward, ef = front(fields, forward_history, family, use_ct=use_ct)
        reverse, er = front(fields, reverse_history, family, use_ct=use_ct)
        joined = np.concatenate([reverse[:0:-1], forward])
        length = float(arc(joined)[-1])
        record = {"seed_id": seed_id, "family": family, "seed_length_vox": seed_length,
                  "seed_xyz": seed.tolist(), "output_length_vox": length,
                  "forward": ef, "reverse": er}
        if length < parameters.min_arc_vox:
            records.append(dict(record, status="short_trace_filtered"))
            continue
        directions = point_directions(joined)
        if tree is not None:
            distance, near = tree.query(joined)
            same = (distance <= parameters.dedup_radius_vox) & (np.abs(np.einsum("ij,ij->i", directions, accepted_directions[family][near])) >= parameters.dedup_tangent_cosine)
            if same.mean() >= parameters.dedup_fraction:
                records.append(dict(record, status="coincident_trace_filtered"))
                continue
        samples = fields.probability(joined, family)
        quality = float(np.quantile(samples, .1))
        output = {"id": len(outputs), "family": family, "points_xyz": joined.tolist(), "gaps": [],
                  "source_curve_ids": [seed_id], "probability_q10": quality,
                  "tracing_mode": "ct-conditioned" if use_ct else "probability-only"}
        outputs.append(output); records.append(dict(record, status="kept", output_id=output["id"]))
        if tree is None:
            accepted_cloud[family] = joined.copy(); accepted_directions[family] = directions.copy()
        else:
            accepted_cloud[family] = np.concatenate([accepted_cloud[family], joined])
            accepted_directions[family] = np.concatenate([accepted_directions[family], directions])
        accepted_trees[family] = cKDTree(accepted_cloud[family])
        if progress is not None:
            progress(number+1, len(seed_rows), len(outputs), sum(arc(np.asarray(o["points_xyz"]))[-1] for o in outputs))
    return outputs, {"parameters": asdict(parameters), "ct_conditioned": use_ct,
                     "seed_count": len(seed_rows), "output_count": len(outputs), "records": records,
                     "reference_as_algorithm_input": False,
                     "bidirectional_scope": "two independent outward walks from the same seed, reverse-flow agreement reserved for later audit"}


REVERSE_GATE = {'reverse_distance_vox': 1.5, 'reverse_cosine': .94, 'min_fraction_each_direction': .9}

def agreement(original, reverse):
    if len(reverse) < 2:
        return {'fraction': 0., 'length_vox': 0., 'mean_distance_vox': None}
    a, v = original[:-1], np.diff(original, axis=0)
    mid = np.mean(np.stack([original[:-1], original[1:]], 1), 1)
    tree = cKDTree(mid)
    points = (reverse[:-1]+reverse[1:])*.5
    direction = np.diff(reverse, axis=0)
    weights = np.linalg.norm(direction, axis=1)
    _, ix = tree.query(points, k=min(12, len(a)), workers=2)
    ix = np.asarray(ix).reshape(len(points), -1)
    aa, vv = a[ix], v[ix]
    projection = np.clip(np.sum((points[:, None]-aa)*vv, axis=-1)/np.maximum(np.sum(vv*vv, axis=-1), 1e-12), 0., 1.)
    error2 = np.sum((points[:, None]-aa-projection[..., None]*vv)**2, axis=-1)
    best = np.argmin(error2, axis=1)
    distance = np.sqrt(error2[np.arange(len(points)), best])
    original_d = vv[np.arange(len(points)), best]
    cosine = np.abs(np.sum(direction*original_d, axis=1))/np.maximum(weights*np.linalg.norm(original_d, axis=1), 1e-12)
    matching = (distance <= REVERSE_GATE['reverse_distance_vox']) & (cosine >= REVERSE_GATE['reverse_cosine'])
    return {'fraction': float(weights[matching].sum()/weights.sum()), 'length_vox': float(weights.sum()),
            'mean_distance_vox': float(np.average(distance, weights=weights)),
            'distance_p90_vox': float(np.quantile(distance, .9)), 'direction_mean_cosine': float(np.average(cosine, weights=weights))}


def reverse_consistent(curves, probabilities, ct, parameters=Parameters()):
    """Return curves passing both fixed reverse-flow arc-agreement checks.

    Inputs are predictions and fixed CT/probability arrays. Every output keeps
    its original connected geometry; the gate filters entire curves.
    """
    fields=Profiles(ct, probabilities, parameters)
    kept,evidence=[],[]
    for curve in curves:
        points=np.asarray(curve['points_xyz'],float)
        results=[]
        for oriented in (points,points[::-1]):
            s=arc(oriented)
            history=at_arc(oriented,s,np.linspace(max(0.,s[-1]-8.),s[-1],5))[::-1]
            reverse,stop=front(fields,history,curve['family'],use_ct=False)
            results.append(dict(agreement(points,reverse),stop=stop['stop']))
        quality=min(row['fraction'] for row in results)
        passed=quality>=REVERSE_GATE['min_fraction_each_direction']
        evidence.append({'curve_id':curve['id'],'passed':passed,'bidirectional_fraction_min':quality,'directions':results})
        if passed:kept.append(dict(curve,bidirectional_fraction_min=quality))
    return kept,{'gate':REVERSE_GATE,'curves':evidence,'reference_as_gate_input':False}
