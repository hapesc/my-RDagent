"""Root conftest to set up Python path for v2 imports."""

import sys

if "." not in sys.path:
    sys.path.insert(0, ".")
