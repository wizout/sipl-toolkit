"""SIPL Language Toolkit: парсер, інтерпретатор, дерево виводу і семантичні терми."""

__version__ = "0.1.0"

from .errors import SiplError, SiplRuntimeError, SiplSyntaxError, SourceSpan
from .parser import parse, parse_tree
from .interpreter import run

__all__ = ["parse", "parse_tree", "run", "SiplError", "SiplSyntaxError",
           "SiplRuntimeError", "SourceSpan", "__version__"]
