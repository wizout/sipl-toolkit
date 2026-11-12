"""Інтерпретатор SIPL: виконує AST на стані змінних.

Стан - це словник {ім'я змінної: ціле число}. Програма невизначена (кидаю
SiplRuntimeError), якщо читається змінна без значення, ділимо на 0, або цикл
не встиг завершитись за max_steps кроків.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ast as A
from .errors import SiplRuntimeError

DEFAULT_MAX_STEPS = 100_000


def apply_arith(op: str, x: int, y: int, span=None) -> int:
    if op == "+":
        return x + y
    if op == "-":
        return x - y
    if op == "*":
        return x * y
    if y == 0:
        raise SiplRuntimeError(f"{op} на нуль не визначено", span)
    # div і mod беру як у математиці для натуральних: 7 div 2 = 3, 7 mod 2 = 1
    return x // y if op == "div" else x % y


def apply_cmp(op: str, x: int, y: int) -> bool:
    return {"<": x < y, "<=": x <= y, "=": x == y,
            "<>": x != y, ">": x > y, ">=": x >= y}[op]


@dataclass
class TraceEvent:
    step: int
    event: str              # "assign", "cond", "skip", "finish"
    span: dict | None
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"step": self.step, "event": self.event, "span": self.span, **self.detail}


class Interpreter:
    def __init__(self, max_steps: int = DEFAULT_MAX_STEPS, trace: bool = False):
        self.max_steps = max_steps
        self.trace_on = trace
        self.trace: list[TraceEvent] = []
        self.steps = 0

    def log(self, event, node, **detail):
        if self.trace_on:
            self.trace.append(TraceEvent(self.steps, event, node.span.to_dict(), detail))

    def tick(self, node):
        self.steps += 1
        if self.steps > self.max_steps:
            raise SiplRuntimeError(
                f"програма не завершилась за {self.max_steps} кроків (можливо, нескінченний цикл)",
                node.span)

    # вирази

    def eval_a(self, e: A.Node, st: dict) -> int:
        if isinstance(e, A.Num):
            return e.value
        if isinstance(e, A.Var):
            if e.name not in st:
                raise SiplRuntimeError(f"змінна {e.name} не має значення", e.span)
            return st[e.name]
        if isinstance(e, A.BinOp):
            return apply_arith(e.op, self.eval_a(e.left, st), self.eval_a(e.right, st), e.span)
        raise TypeError(type(e).__name__)

    def eval_b(self, b: A.Node, st: dict) -> bool:
        if isinstance(b, A.BoolConst):
            return b.value
        if isinstance(b, A.Compare):
            return apply_cmp(b.op, self.eval_a(b.left, st), self.eval_a(b.right, st))
        if isinstance(b, A.Not):
            return not self.eval_b(b.operand, st)
        if isinstance(b, A.BoolOp):
            # обидві частини рахую завжди, як у композиційній семантиці S^2(or, ...)
            x, y = self.eval_b(b.left, st), self.eval_b(b.right, st)
            return (x and y) if b.op == "and" else (x or y)
        raise TypeError(type(b).__name__)

    # оператори

    def exec(self, s: A.Node, st: dict) -> dict:
        if isinstance(s, A.Program):
            st = self.exec(s.body, st)
            self.log("finish", s, state=dict(st))
            return st
        if isinstance(s, A.Assign):
            self.tick(s)
            v = self.eval_a(s.expr, st)
            st = {**st, s.var: v}          # st ∇ [x ↦ v], старий стан не чіпаю
            self.log("assign", s, var=s.var, value=v, state=dict(st))
            return st
        if isinstance(s, A.Seq):
            return self.exec(s.second, self.exec(s.first, st))
        if isinstance(s, A.If):
            self.tick(s)
            c = self.eval_b(s.cond, st)
            self.log("cond", s.cond, kind="if", value=c)
            return self.exec(s.then if c else s.else_, st)
        if isinstance(s, A.While):
            while True:
                self.tick(s)
                c = self.eval_b(s.cond, st)
                self.log("cond", s.cond, kind="while", value=c)
                if not c:
                    return st
                st = self.exec(s.body, st)
        if isinstance(s, A.Block):
            return self.exec(s.body, st)
        if isinstance(s, A.Skip):
            self.tick(s)
            self.log("skip", s)
            return st
        raise TypeError(type(s).__name__)


def run(program: A.Program, state: dict | None = None,
        max_steps: int = DEFAULT_MAX_STEPS, trace: bool = False):
    """Виконує програму. Повертає (кінцевий стан, interp), в interp.trace - події."""
    it = Interpreter(max_steps, trace)
    return it.exec(program, dict(state or {})), it
