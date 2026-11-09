"""SIPL Language Toolkit: парсер, інтерпретатор, дерево виводу і семантичні терми."""

__version__ = "0.1.0"

from .errors import SiplError, SiplSyntaxError, SourceSpan

__all__ = ["SiplError", "SiplSyntaxError", "SourceSpan", "__version__"]
