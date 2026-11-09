"""The same fixed logit probability scale used by the incoming-flow probe."""
import numpy as np

def bounded_maps(family_probability, ct_dog_z, radial_squared):
    p = np.asarray(family_probability, np.float32)
    z = np.asarray(ct_dog_z, np.float32)
    assert p.shape == z.shape and p.ndim in (2, 3)
    assert np.isfinite(p).all() and np.isfinite(z).all()
    clipped = np.clip(p, 1e-5, 1.-1e-5)
    energy = np.log(clipped)-np.log1p(-clipped)
    prior = np.asarray(radial_squared)/8.
    return {'probability-only': np.where(p >= .5, energy-prior, -np.inf),
            'ct-energy-control': np.where(p >= .5, energy+z-prior, -np.inf)}
