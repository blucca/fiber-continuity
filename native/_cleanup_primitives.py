"""Measured SciPy primitive bodies used by pinned ExteriorBlack cleanup.

Hole filling uses the default 6-connected background. Radius-one cube
morphology has a zero-valued border. The operation bodies are reused from
the measured CPU adapter; this process-local installer registers these two
vc_reader calls. Native cut/thin logic comes from the supplied pinned source.
"""
import sys
import types
import numpy as np
from scipy import ndimage as ndi


def fill_holes(mask, *, connectivity=0, threads=0, out=None):
    assert connectivity == 0 and out is None
    return ndi.binary_fill_holes(mask)


class Morphology:
    def __init__(self, operation, *, radius, footprint):
        assert operation in ("dilate", "erode") and radius == 1 and footprint == "cube"
        self.operation = operation

    def __call__(self, channels):
        assert channels.ndim == 4
        function = ndi.binary_dilation if self.operation == "dilate" else ndi.binary_erosion
        # Pinned Morphology.neutral_border=False: outside values are zero.
        return np.stack([function(a, structure=np.ones((3, 3, 3), dtype=bool),
                                  border_value=0) for a in channels])


def install():
    parent = types.ModuleType("vc_reader")
    parent.__path__ = []
    modules = {"geometry": {"fill_holes": fill_holes},
               "transforms": {"Morphology": Morphology}}
    sys.modules["vc_reader"] = parent
    for name, members in modules.items():
        module = types.ModuleType("vc_reader." + name)
        module.__dict__.update(members)
        setattr(parent, name, module)
        sys.modules[module.__name__] = module
