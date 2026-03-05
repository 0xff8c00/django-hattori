"""Backwards-compatibility shim: redirects all ninja.* imports to hattori.*"""

import importlib
import sys
import warnings


class _NinjaImportRedirector:
    """Meta path finder that redirects ninja.* imports to hattori.* with a deprecation warning."""

    @classmethod
    def find_module(cls, fullname, path=None):
        if fullname == "ninja" or fullname.startswith("ninja."):
            return cls
        return None

    @classmethod
    def load_module(cls, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        new_name = "hattori" + fullname[5:]
        warnings.warn(
            f"Importing from '{fullname}' is deprecated, use '{new_name}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        mod = importlib.import_module(new_name)
        sys.modules[fullname] = mod
        return mod


# Install the redirector and immediately redirect this module
sys.meta_path.insert(0, _NinjaImportRedirector)
_mod = importlib.import_module("hattori")
sys.modules[__name__] = _mod
