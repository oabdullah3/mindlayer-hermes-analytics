"""Hermes Analytics Plugin — entry point.

This is the root-level plugin entry that hermes discovers.
Delegates to userend/ for the full implementation.
"""

from pathlib import Path
import sys

# Ensure userend/ is importable as a package
_plugin_root = Path(__file__).parent
_userend = _plugin_root / "userend"
if str(_userend) not in sys.path:
    sys.path.insert(0, str(_userend))

# Delegate register() to the real implementation in userend/
from userend import register  # noqa: E402, F401
