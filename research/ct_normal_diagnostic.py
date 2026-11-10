"""Native CT intensity normal, independent of a predicted fiber's tangent.

Fixed 1-voxel derivative / 3-voxel integration scales match the R529 diagnostic.
Physical carrier identity requires anchored branch correspondences and controls.
"""
import numpy as np
from scipy import ndimage as ndi


def ct_normal(ct_zyx, xyz):
    """Return (unit normal XYZ, ascending tensor eigenvalues), or None.

    Input coordinates are native voxel XYZ. Full original 33^3 CT context and
    non-flat gradient energy are required. This returns an intensity axis;
    carrier lineage and repair decisions are evaluated by the consuming task.
    """
    ct = np.asarray(ct_zyx)
    q = np.asarray(xyz, dtype=float)
    assert ct.ndim == 3 and q.shape == (3,) and np.all(np.isfinite(q))
    c = np.rint(q).astype(int)
    lo, hi = c - 16, c + 17
    if np.any(lo < 0) or np.any(hi > np.array(ct.shape[::-1])):
        return None
    patch = np.asarray(ct[lo[2]:hi[2], lo[1]:hi[1], lo[0]:hi[0]], np.float32)
    gradients = [ndi.gaussian_filter(patch, 1., order=o, mode='nearest', truncate=4.)
                 for o in ((0, 0, 1), (0, 1, 0), (1, 0, 0))]
    z, y, x = np.indices(patch.shape, dtype=np.float32)
    coordinates = np.stack((x + lo[0], y + lo[1], z + lo[2]), -1)
    weights = np.exp(-np.sum((coordinates - q) ** 2, axis=-1) / (2. * 3. ** 2))
    weights /= weights.sum()
    tensor = np.array([[np.sum(weights * a * b) for b in gradients]
                       for a in gradients], dtype=np.float64)
    values, vectors = np.linalg.eigh(tensor)
    if values[-1] <= 1e-12:
        return None
    normal = vectors[:, -1]
    if normal[np.argmax(np.abs(normal))] < 0:
        normal = -normal
    return normal, values


def sheet_frame(unit_ct_normal, fiber_tangent):
    """Return in-plane tangent/lateral axes while retaining the CT normal.

    The normal comes from ct_normal. A vanishing in-plane direction returns
    None; a correct-layer anchor supplies direction for a re-tracing task.
    """
    n = np.asarray(unit_ct_normal, float)
    t = np.asarray(fiber_tangent, float)
    projected = t - n * np.dot(n, t)
    length = np.linalg.norm(projected)
    if length <= 1e-8:
        return None
    inplane = projected / length
    return inplane, np.cross(inplane, n)
