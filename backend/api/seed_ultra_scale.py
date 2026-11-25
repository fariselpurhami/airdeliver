"""Historical maintenance entrypoint. Operational approval requirements unchanged."""
from importlib import import_module as _import_module
import runpy as _runpy
import sys as _sys

if __name__ == '__main__':
    _runpy.run_module('tools.seed_ultra_scale', run_name='__main__')
else:
    _sys.modules[__name__] = _import_module('tools.seed_ultra_scale')
