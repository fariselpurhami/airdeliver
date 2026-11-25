"""Compatibility import retaining one module object and shared state."""
from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module('app.services.cart.cart_lifecycle_review')
