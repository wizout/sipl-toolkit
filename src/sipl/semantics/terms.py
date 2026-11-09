"""Семантичні терми в нотації курсу і їх запис текстом.

  Const(1)        1̄          константа (функція, що на будь-якому стані дає 1)
  Deref("N")      N⇒         розіменування: значення змінної N у стані
  Sup("gr", a, b) S²(gr, a, b) суперпозиція: gr(a(st), b(st))
  AS("R", t)      ASᴿ(t)     присвоєння: st ∇ [R ↦ t(st)]
  Comp(f, g)      f · g      композиція: спочатку f, потім g
  IF(p, f, g)     IF(p, f, g)
  WH(p, f)        WH(p, f)
  Id()            id
"""

from __future__ import annotations

from dataclasses import dataclass

# назви базових функцій, як у практичних
ARITH_FN = {"+": "add", "-": "sub", "*": "mult", "div": "div", "mod": "mod"}
CMP_FN = {"<": "ls", "<=": "leq", "=": "eq", "<>": "neq", ">": "gr", ">=": "geq"}
BOOL_FN = {"and": "and", "or": "or", "not": "neg"}


class Term:
    def render(self, fmt: str = "text") -> str:
        return render(self, fmt)

    def __str__(self) -> str:
        return render(self, "text")


@dataclass(frozen=True)
class Const(Term):
    value: int | bool


@dataclass(frozen=True)
class Deref(Term):
    var: str


@dataclass(frozen=True)
class Sup(Term):
    fn: str
    args: tuple


@dataclass(frozen=True)
class AS(Term):
    var: str
    expr: Term


@dataclass(frozen=True)
class Comp(Term):
    first: Term
    second: Term


@dataclass(frozen=True)
class IF(Term):
    cond: Term
    then: Term
    else_: Term


@dataclass(frozen=True)
class WH(Term):
    cond: Term
    body: Term


@dataclass(frozen=True)
class Id(Term):
    pass


# ---------- запис термів ----------

OVER = "̅"   # комбінована риска зверху, ставлю після кожного символу константи


def const_str(v, fmt="text") -> str:
    s = ("true" if v else "false") if isinstance(v, bool) else str(v)
    if fmt == "latex":
        return r"\overline{%s}" % s
    if fmt == "ascii":
        return "~" + s
    return "".join(c + OVER for c in s)


def render(t: Term, fmt: str = "text") -> str:
    L = fmt == "latex"
    arrow = r"\Rightarrow" if L else ("=>" if fmt == "ascii" else "⇒")
    dot = r" \cdot " if L else (" . " if fmt == "ascii" else " · ")

    def name(s):           # назви функцій та операторів
        return r"\mathit{%s}" % s if L else s

    def r(t):
        if isinstance(t, Const):
            return const_str(t.value, fmt)
        if isinstance(t, Deref):
            return f"{t.var}{arrow}"
        if isinstance(t, Sup):
            n = len(t.args)
            head = f"S^{{{n}}}" if L else f"S^{n}"
            return head + "(" + ", ".join([name(t.fn)] + [r(a) for a in t.args]) + ")"
        if isinstance(t, AS):
            head = r"\mathit{AS}^{%s}" % t.var if L else f"AS^{t.var}"
            return f"{head}({r(t.expr)})"
        if isinstance(t, Comp):
            # S1; S2; S3 = (S1; S2); S3, тому ліву композицію беру в дужки, як у практичній
            a = r(t.first)
            if isinstance(t.first, Comp):
                a = f"({a})"
            b = r(t.second)
            if isinstance(t.second, Comp):
                b = f"({b})"
            return a + dot + b
        if isinstance(t, IF):
            return f"{name('IF')}({r(t.cond)}, {r(t.then)}, {r(t.else_)})"
        if isinstance(t, WH):
            return f"{name('WH')}({r(t.cond)}, {r(t.body)})"
        if isinstance(t, Id):
            return name("id")
        raise TypeError(type(t).__name__)

    return r(t)


def short(t: Term, fmt: str = "text", limit: int = 40) -> str:
    """Короткий запис для трасування: довгий терм скорочую до IF(...), WH(...)."""
    full = render(t, fmt)
    if len(full) <= limit:
        return full
    if isinstance(t, Comp):
        return short(t.first, fmt, limit // 2) + (" . " if fmt == "ascii" else " · ") + \
            short(t.second, fmt, limit // 2)
    if isinstance(t, AS):
        return f"AS^{t.var}(...)"
    if isinstance(t, Sup):
        return f"S^{len(t.args)}({t.fn}, ...)"
    return type(t).__name__ + "(...)"


def to_dict(t: Term) -> dict:
    if isinstance(t, Const):
        return {"term": "Const", "value": t.value}
    if isinstance(t, Deref):
        return {"term": "Deref", "var": t.var}
    if isinstance(t, Sup):
        return {"term": "Sup", "fn": t.fn, "args": [to_dict(a) for a in t.args]}
    if isinstance(t, AS):
        return {"term": "AS", "var": t.var, "expr": to_dict(t.expr)}
    if isinstance(t, Comp):
        return {"term": "Comp", "first": to_dict(t.first), "second": to_dict(t.second)}
    if isinstance(t, IF):
        return {"term": "IF", "cond": to_dict(t.cond), "then": to_dict(t.then),
                "else": to_dict(t.else_)}
    if isinstance(t, WH):
        return {"term": "WH", "cond": to_dict(t.cond), "body": to_dict(t.body)}
    return {"term": "Id"}
