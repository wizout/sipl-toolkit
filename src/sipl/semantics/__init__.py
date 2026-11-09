"""Композиційна семантика SIPL: побудова термів (SEM-01) і їх обчислення (SEM-02)."""

from .build import RULE_TEXT, build_term, explain
from .evaluate import EvalResult, evaluate
from .terms import AS, IF, WH, Comp, Const, Deref, Id, Sup, Term, render

__all__ = ["build_term", "explain", "evaluate", "EvalResult", "render", "RULE_TEXT",
           "Term", "Const", "Deref", "Sup", "AS", "Comp", "IF", "WH", "Id"]
