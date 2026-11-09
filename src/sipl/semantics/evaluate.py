"""Обчислення семантичного терму на стані з поясненням кожного переходу (як тестування
в практичній 2).

Правила застосування (AF_*):
  AF_SEQ  (f · g)(st) = g(f(st))
  AF_S    S^n(h, f1, ..., fn)(st) = h(f1(st), ..., fn(st))
  AF_DNM  x⇒(st) = st(x), невизначено, якщо x немає в st
  AF_AS   AS^x(f)(st) = st ∇ [x ↦ f(st)]
  AF_IF   IF(p, f, g)(st) = f(st), якщо p(st) = true, і g(st), якщо false
  AF_ID   id(st) = st
  AF_WH   WH(p, f)(st) = st, якщо p(st) = false, і WH(p, f)(f(st)), якщо true
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..interpreter import apply_arith
from .terms import AS, IF, WH, Comp, Const, Deref, Id, Sup, Term, const_str, render, short

DEFAULT_MAX_ITERATIONS = 1000

AF_TEXT = {
    "AF_SEQ": "(f · g)(st) = g(f(st))",
    "AF_S":   "S^n(h, f1, ..., fn)(st) = h(f1(st), ..., fn(st))",
    "AF_DNM": "x⇒(st) = st(x), невизначено, якщо x немає в st",
    "AF_AS":  "AS^x(f)(st) = st ∇ [x ↦ f(st)]",
    "AF_IF":  "IF(p, f, g)(st) = f(st), якщо p(st) = true, і g(st), якщо false",
    "AF_ID":  "id(st) = st",
    "AF_WH":  "WH(p, f)(st) = st, якщо p(st) = false, і WH(p, f)(f(st)), якщо true",
}
SUB_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

FUNCS = {
    "add": lambda x, y: x + y, "sub": lambda x, y: x - y, "mult": lambda x, y: x * y,
    "ls": lambda x, y: x < y, "leq": lambda x, y: x <= y, "eq": lambda x, y: x == y,
    "neq": lambda x, y: x != y, "gr": lambda x, y: x > y, "geq": lambda x, y: x >= y,
    "and": lambda x, y: x and y, "or": lambda x, y: x or y, "neg": lambda x: not x,
}


class Undefined(Exception):
    """Значення терму на цьому стані невизначене (⊥)."""


def show(v) -> str:
    return ("true" if v else "false") if isinstance(v, bool) else str(v)


def call(fn: str, args: list):
    if fn in ("div", "mod"):
        if args[1] == 0:
            raise Undefined(f"{fn}({args[0]}, 0) невизначено: ділення на нуль")
        return apply_arith(fn, *args)
    return FUNCS[fn](*args)


@dataclass
class Step:
    rules: list[str]
    text: str
    kind: str = "step"      # "step", "header", "result"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "rules": self.rules, "text": self.text}


@dataclass
class EvalResult:
    term: Term
    initial: dict
    state: dict | None = None        # None, якщо результат невизначений
    undefined: str | None = None
    value: object = None             # для терму-виразу (не оператора)
    steps: list[Step] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"initial": self.initial, "defined": self.state is not None,
                "state": self.state, "value": self.value, "undefined": self.undefined,
                "steps": [s.to_dict() for s in self.steps]}

    def text(self) -> str:
        out = []
        for s in self.steps:
            if s.kind == "header":
                out.append("")
                out.append(s.text)
            elif s.rules:
                out.append(", ".join(s.rules) + ": " + s.text)
            else:
                out.append(s.text)
        return "\n".join(out)


class Evaluator:
    def __init__(self, fmt: str = "text", max_iterations: int = DEFAULT_MAX_ITERATIONS):
        self.fmt = "ascii" if fmt == "ascii" else "text"
        self.max_iterations = max_iterations
        self.iterations = 0
        self.counter = 0
        self.steps: list[Step] = []
        a = self.fmt == "ascii"
        self.MAPS = "->" if a else "↦"
        self.NABLA = " <| " if a else "∇"

    # ---------- допоміжне ----------

    def r(self, t: Term) -> str:
        return render(t, self.fmt)

    def sh(self, t: Term) -> str:
        return short(t, self.fmt)

    def st_str(self, st: dict) -> str:
        return "[" + ", ".join(f"{k} {self.MAPS} {show(v)}" for k, v in st.items()) + "]"

    def new_name(self) -> str:
        self.counter += 1
        return f"st_{self.counter}" if self.fmt == "ascii" else \
            "st" + str(self.counter).translate(SUB_DIGITS)

    def add(self, rules, text, kind="step"):
        self.steps.append(Step(rules, text, kind))

    # ---------- вирази: ланцюжок рівностей ----------

    def expanded(self, t: Term, sn: str) -> str:
        # S^2(add, D⇒, 1̄)(st) -> add(D⇒(st), 1̄(st))  (AF_S, розкрито до кінця)
        if isinstance(t, Sup):
            return f"{t.fn}(" + ", ".join(self.expanded(a, sn) for a in t.args) + ")"
        return f"{self.r(t)}({sn})"

    def leaves(self, t: Term, st: dict, sn: str):
        # підставляю значення змінних і констант, функції ще не рахую
        if isinstance(t, Const):
            return t.value
        if isinstance(t, Deref):
            if t.var not in st:
                raise Undefined(f"{t.var}{'=>' if self.fmt == 'ascii' else '⇒'}({sn}) "
                                f"невизначено: змінної {t.var} немає в стані")
            return st[t.var]
        return (t.fn, [self.leaves(a, st, sn) for a in t.args])

    @staticmethod
    def tree_str(v) -> str:
        if isinstance(v, tuple):
            return f"{v[0]}(" + ", ".join(Evaluator.tree_str(a) for a in v[1]) + ")"
        return show(v)

    @staticmethod
    def reduce(v):
        # рахую всі функції, у яких аргументи вже числа (найглибший рівень)
        if not isinstance(v, tuple):
            return v
        fn, args = v
        if all(not isinstance(a, tuple) for a in args):
            return call(fn, args)
        return (fn, [Evaluator.reduce(a) for a in args])

    def chain(self, t: Term, st: dict, sn: str) -> tuple[object, list[str]]:
        """Повертає значення і список кроків: [розкритий запис, підстановка, ..., значення]."""
        parts = [f"{self.r(t)}({sn})"] if isinstance(t, Sup) else []
        parts.append(self.expanded(t, sn))
        try:
            v = self.leaves(t, st, sn)
            while True:
                s = self.tree_str(v)
                if s != parts[-1]:
                    parts.append(s)
                if not isinstance(v, tuple):
                    return v, parts
                v = self.reduce(v)
        except Undefined as e:
            self.add([], " = ".join(parts) + " = ⊥")
            raise e

    @staticmethod
    def expr_rules(t: Term) -> list[str]:
        out = []

        def walk(x):
            if isinstance(x, Sup):
                if "AF_S" not in out:
                    out.append("AF_S")
                for a in x.args:
                    walk(a)
            elif isinstance(x, Deref) and "AF_DNM" not in out:
                out.append("AF_DNM")
        walk(t)
        out.sort(key=lambda r: r != "AF_S")
        return out

    def cond(self, p: Term, st: dict, sn: str) -> bool:
        v, parts = self.chain(p, st, sn)
        self.add(self.expr_rules(p), " = ".join(parts))
        if not isinstance(v, bool):
            raise Undefined(f"умова дала число {v}, а не true/false")
        return v

    # ---------- оператори ----------

    @staticmethod
    def flat(t: Term) -> list[Term]:
        if isinstance(t, Comp):
            return Evaluator.flat(t.first) + Evaluator.flat(t.second)
        return [t]

    def app(self, t: Term, sn: str) -> str:
        s = self.sh(t)
        return f"({s})({sn})" if isinstance(t, Comp) else f"{s}({sn})"

    def exec(self, t: Term, st: dict, sn: str) -> tuple[dict, str]:
        if isinstance(t, Comp):
            # f1 · f2 · ... · fn розгортаю одним кроком: fn(...f2(f1(st)))
            parts = self.flat(t)
            names = [self.sh(f) for f in parts]
            inner = sn
            for n in names:
                inner = f"{n}({inner})"
            dot = " . " if self.fmt == "ascii" else " · "
            self.add(["AF_SEQ"], f"({dot.join(names)})({sn}) = {inner}")
            for f in parts:
                st, sn = self.exec(f, st, sn)
            return st, sn

        if isinstance(t, AS):
            v, parts = self.chain(t.expr, st, sn)
            if isinstance(t.expr, Sup):
                parts = parts[1:]
            new = {**st, t.var: v}
            name = self.new_name()
            lines = [f"{sn}{self.NABLA}[{t.var} {self.MAPS} {p}]" for p in parts]
            self.add(["AF_AS"] + self.expr_rules(t.expr),
                     f"{self.r(t)}({sn}) = " + " = ".join(lines) +
                     f" = {self.st_str(new)} = {name}")
            return new, name

        if isinstance(t, IF):
            c = self.cond(t.cond, st, sn)
            branch = t.then if c else t.else_
            self.add(["AF_IF"], f"{self.sh(t)}({sn}) = {self.app(branch, sn)}, "
                                f"бо умова {show(c)}")
            return self.exec(branch, st, sn)

        if isinstance(t, Id):
            self.add(["AF_ID"], f"id({sn}) = {sn}")
            return st, sn

        if isinstance(t, WH):
            k = 0
            while True:
                c = self.cond(t.cond, st, sn)
                if not c:
                    self.add(["AF_WH"], f"{self.sh(t)}({sn}) = {sn}, умова false - цикл завершено")
                    return st, sn
                k += 1
                self.iterations += 1
                if self.iterations > self.max_iterations:
                    raise Undefined(f"цикл не завершився за {self.max_iterations} ітерацій, "
                                    "значення вважаю невизначеним")
                self.add([], f"Ітерація {k}", "header")
                self.add(["AF_WH"], f"{self.sh(t)}({sn}) = {self.sh(t)}({self.app(t.body, sn)})")
                st, sn = self.exec(t.body, st, sn)

        # окремий вираз (не оператор): просто рахую значення
        v, parts = self.chain(t, st, sn)
        self.add(self.expr_rules(t), " = ".join(parts))
        return {"value": v}, sn


def evaluate(term: Term, state: dict, fmt: str = "text",
             max_iterations: int = DEFAULT_MAX_ITERATIONS) -> EvalResult:
    ev = Evaluator(fmt, max_iterations)
    res = EvalResult(term, dict(state))
    ev.add([], f"st = {ev.st_str(state)}")
    try:
        st, sn = ev.exec(term, dict(state), "st")
        if isinstance(term, (Sup, Const, Deref)):
            res.state, res.value = dict(state), st["value"]
            ev.add([], f"Результат: {show(res.value)}", "result")
        else:
            res.state = st
            ev.add([], f"Результат: {sn} = {ev.st_str(st)}", "result")
    except Undefined as e:
        res.undefined = str(e)
        ev.add([], f"Результат: невизначено (⊥) - {e}", "result")
    res.steps = ev.steps
    return res
