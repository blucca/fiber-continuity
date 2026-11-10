"""Bounded centre-path optimization with a same-station pointwise control.

Both operators read the same original-arc stations, CT/P energies, endpoint and
context constraints, and use the pinned displacement smoother/native cleanup.
Only DP maximizes the integrated energy minus world-displacement variation.
"""
import hashlib
import numpy as np
from scipy import ndimage as ndi
from bounded_logit_recenter import (Parameters, arclength, at_arc, incoming_tangents,
    frames, sample, smooth_displacements, validate_traces)
from transverse_centering import center_scores
from logit_maps import bounded_maps

PARAMETERS = {
    'station_step_max_vox': 1.0, 'incoming_tangent_support_vox': 8.0,
    'context_radius_vox': 8.0, 'transverse_grid_step_vox': .5,
    'displacement_radius_vox': 1.5, 'candidate_count': 29,
    'probability_gate': .5, 'probability_logit_clip': 1e-5,
    'displacement_prior': 'r2/8', 'ct_fine_sigma_vox': 1., 'ct_fine_truncate': 4.,
    'ct_background_sigma_vox': 2., 'ct_background_truncate': 2.,
    'ct_mad_radius_vox': 6., 'ct_mad_scale': 1.4826, 'ct_mad_floor_gray': 1.,
    'integration': 'original-arc trapezoid weights',
    'world_transition_diffusion_vox2_per_arc_vox': .25,
    'world_transition_cost': '2*norm(d_i-d_previous)^2 / delta_original_arc',
    'allowed_transitions': 'all finite states; soft continuity cost',
    'unsupported_station': 'zero displacement, neutral unary',
    'endpoint_selected_state': 'zero in both operators',
    'post_smoothing_sigma_vox': 2., 'post_smoothing_step_max_vox': .5,
    'post_smoothing': 'same pinned original-arc Gaussian/transverse/domain/cap/endpointpin',
    'topology_edits': 0, 'primary': 'dp', 'causal_control': 'pointwise',
}
AXIS = np.arange(-8., 8.01, .5)
UU, VV = np.meshgrid(AXIS, AXIS, indexing='ij')
R2 = UU*UU + VV*VV
MASK = R2 <= 1.5**2 + 1e-8
UV = np.c_[UU[MASK], VV[MASK]]
RADIAL = R2[MASK]
ZERO = int(np.flatnonzero(RADIAL == 0)[0])
assert len(UV) == 29


def arc_weights(arc):
    steps = np.diff(arc)
    assert len(steps) and np.all(steps > 0)
    return np.r_[steps[0]/2, (steps[:-1]+steps[1:])/2, steps[-1]/2]


def path_objective(energy, vectors, arc, indices):
    chosen = vectors[np.arange(len(arc)), indices]
    integrated = float(np.sum(arc_weights(arc)*energy[np.arange(len(arc)), indices]))
    penalty = float(np.sum(2*np.sum(np.diff(chosen, axis=0)**2, axis=1)/np.diff(arc)))
    return integrated-penalty, integrated, penalty


def viterbi(energy, vectors, arc):
    """Exact finite-state optimum; physical vectors define all transition costs."""
    energy = np.asarray(energy, np.float64)
    vectors = np.asarray(vectors, np.float64)
    assert energy.shape == vectors.shape[:2] and vectors.shape[-1] == 3
    assert len(energy) == len(arc) and np.isfinite(energy).any(axis=1).all()
    weight = arc_weights(arc)
    value = weight[0]*energy[0]
    back = np.zeros(energy.shape, np.uint8)
    for i in range(1, len(arc)):
        difference = vectors[i-1, :, None, :] - vectors[i, None, :, :]
        transition = 2*np.sum(difference*difference, axis=2)/(arc[i]-arc[i-1])
        scores = value[:, None] - transition
        parent = np.argmax(scores, axis=0)
        back[i] = parent
        value = weight[i]*energy[i] + scores[parent, np.arange(len(parent))]
    indices = np.empty(len(arc), int)
    indices[-1] = int(np.argmax(value))
    for i in range(len(arc)-1, 0, -1):
        indices[i-1] = int(back[i, indices[i]])
    assert np.isfinite(value[indices[-1]])
    return indices


def station_energy(points, original_arc, probabilities_family, ct1):
    length = original_arc[-1]
    arc = np.linspace(0., length, int(np.ceil(length))+1)
    centres = at_arc(points, original_arc, arc)
    tangent = centres-at_arc(points, original_arc, np.maximum(0., arc-8.))
    norm = np.linalg.norm(tangent, axis=1)
    empty = norm < 1e-10
    tangent[empty] = (at_arc(points, original_arc, np.minimum(length, arc+8.))-centres)[empty]
    norm = np.linalg.norm(tangent, axis=1)
    if np.any(norm < 1e-10):
        raise ValueError('original curve has a zero-geometry station tangent')
    tangent /= norm[:, None]
    u, v = frames(tangent)
    vectors = u[:, None, :]*UV[None, :, :1] + v[:, None, :]*UV[None, :, 1:]
    energy = np.empty((len(arc), 29), np.float64)
    supported = np.zeros(len(arc), bool)
    size_xyz = np.asarray(ct1.shape[::-1], float)
    for low in range(0, len(arc), 96):
        high = min(low+96, len(arc))
        xyz = centres[low:high, None, None] + u[low:high, None, None]*UU[None, ..., None] + v[low:high, None, None]*VV[None, ..., None]
        complete = ((xyz >= 0.) & (xyz <= size_xyz-1.)).all((1, 2, 3))
        cp, fp = sample(ct1, xyz), sample(probabilities_family, xyz)
        _, evidence = center_scores(cp, fp)
        values = bounded_maps(fp, evidence['dog_z'], R2)['ct-energy-control'][:, MASK]
        values = np.asarray(values, np.float64)-1e-8*RADIAL[None]
        supported[low:high] = complete & np.isfinite(values).any(axis=1)
        values[~supported[low:high]] = -np.inf
        values[~supported[low:high], ZERO] = 0.
        energy[low:high] = values
    # Endpoint constraints are shared, including the pointwise causal control.
    for endpoint in (0, -1):
        original = energy[endpoint, ZERO]
        energy[endpoint] = -np.inf
        energy[endpoint, ZERO] = original if np.isfinite(original) else 0.
    assert np.isfinite(energy).any(axis=1).all()
    return arc, energy, vectors, supported


def recenter_pair(traces, probabilities, ct, progress=None):
    if ct.ndim != 3 or ct.dtype != np.uint8 or probabilities.dtype != np.float32 or probabilities.shape != (4,)+ct.shape:
        raise ValueError('CT uint8 ZYX and probabilities float32 4ZYX required')
    validate_traces(traces, ct.shape)
    ct1 = ndi.gaussian_filter(ct.astype(np.float32), 1., mode='nearest', truncate=4.)
    family = {'V': probabilities[1]+probabilities[3], 'H': probabilities[2]+probabilities[3]}
    outputs = {'pointwise': [], 'dp': []}
    diagnostics = []
    for number, curve in enumerate(traces['curves']):
        points = np.asarray(curve['points_xyz'], float)
        original_arc = arclength(points)
        arc, energy, vectors, supported = station_energy(points, original_arc, family[curve['family']], ct1)
        indices = {'pointwise': np.argmax(energy, axis=1), 'dp': viterbi(energy, vectors, arc)}
        objectives = {mode: path_objective(energy, vectors, arc, value) for mode, value in indices.items()}
        assert objectives['dp'][0] >= objectives['pointwise'][0]-1e-7
        tangent = incoming_tangents(points, original_arc, 8.)
        shifts = {}
        for mode in outputs:
            selected = vectors[np.arange(len(arc)), indices[mode]]
            knots = at_arc(selected, arc, original_arc)
            shift, _ = smooth_displacements(knots, points, original_arc, tangent, np.asarray(ct.shape[::-1], float), Parameters())
            moved = points+shift
            assert np.isfinite(moved).all() and ((moved >= 0.) & (moved <= np.asarray(ct.shape[::-1])-1.)).all()
            assert np.linalg.norm(shift, axis=1).max() <= 1.5+1e-8
            assert np.abs(np.einsum('ij,ij->i', shift, tangent)).max() < 1e-8
            assert np.array_equal(moved[[0, -1]], points[[0, -1]])
            result = dict(curve, points_xyz=moved.tolist(), source_curve_ids=curve.get('source_curve_ids', [str(curve['id'])]))
            assert result['id'] == curve['id'] and result.get('gaps', []) == curve.get('gaps', []) and len(moved) == len(points)
            outputs[mode].append(result)
            shifts[mode] = {'mean_vox': float(np.linalg.norm(shift, axis=1).mean()), 'max_vox': float(np.linalg.norm(shift, axis=1).max())}
        diagnostics.append({'source_id': str(curve['id']), 'stations': len(arc), 'unsupported_stations': int((~supported).sum()),
            'shared_energy_sha256': hashlib.sha256(energy.tobytes()).hexdigest(),
            'changed_selected_stations': int(np.count_nonzero(indices['pointwise'] != indices['dp'])),
            'objective': {mode: {'total': value[0], 'integrated_energy': value[1], 'transition_penalty': value[2]} for mode, value in objectives.items()},
            'smoothed_shift': shifts})
        if progress and (number % 25 == 0 or number+1 == len(traces['curves'])):
            progress(number+1, len(traces['curves']))
    metadata = {key: value for key, value in traces.items() if key not in ('curves', 'count', 'length_voxels')}
    envelopes = {mode: dict(metadata, stage='continuous-centre-path-'+mode, curves=curves, count=len(curves),
        length_voxels=sum(float(arclength(np.asarray(c['points_xyz']))[-1]) for c in curves), centre_path_parameters=PARAMETERS,
        labels_as_algorithm_input=False, topology_edits=0) for mode, curves in outputs.items()}
    return envelopes, diagnostics
