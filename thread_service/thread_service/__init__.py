"""Thread persistence service package."""

from importlib.metadata import version, PackageNotFoundError

try:  # pragma: no cover - fallback for editable installs
    __version__ = version("thread-service")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["__version__"]
