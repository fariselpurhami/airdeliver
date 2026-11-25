"""Compatibility import for the provider-capacity domain, one module identity."""
from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module('app.services.provider_capacity.shared_provider_admission')
