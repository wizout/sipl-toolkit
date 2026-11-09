"""SIPL Language Toolkit: парсер, інтерпретатор, дерево виводу і семантичні терми."""

__version__ = "0.1.0"

from .errors import SiplError, SiplSyntaxError, SourceSpan
from .parser import parse, parse_tree

__all__ = ["parse", "parse_tree", "SiplError", "SiplSyntaxError", "SourceSpan", "__version__"]
