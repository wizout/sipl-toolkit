"""Побудова семантичного терму з AST за правилами NS_* (практична 2).

Терм будується рекурсивно: кожен вузол AST перетворюється за своїм правилом,
а замість дітей підставляються їхні терми.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import ast as A
from .terms import (AS, ARITH_FN, BOOL_FN, CMP_FN, IF, WH, Comp, Const, Deref, Id, Sup,
                    Term, render)

ARITH_RULE = {"+": "NS_A_Add", "-": "NS_A_Sub", "*": "NS_A_Mult",
              "div": "NS_A_Div", "mod": "NS_A_Mod"}
CMP_RULE = {"<": "NS_B_ls", "<=": "NS_B_leq", "=": "NS_B_eq",
            "<>": "NS_B_neq", ">": "NS_B_gr", ">=": "NS_B_geq"}

# самі правила, щоб показувати їх у поясненні та в документації
RULE_TEXT = {
    "NS_Prog":     "sem_P(begin S end) = sem_S(S)",
    "NS_Stm_Seq":  "sem_S(S1; S2) = sem_S(S1) · sem_S(S2)",
    "NS_Stm_As":   "sem_S(x := a) = AS^x(sem_A(a))",
    "NS_Stm_If":   "sem_S(if b then S1 else S2) = IF(sem_B(b), sem_S(S1), sem_S(S2))",
    "NS_Stm_Wh":   "sem_S(while b do S) = WH(sem_B(b), sem_S(S))",
    "NS_Stm_BE":   "sem_S(begin S end) = sem_S(S)",
    "NS_Stm_skip": "sem_S(skip) = id",
    "NS_A_Num":    "sem_A(n) = n̄",
    "NS_A_Var":    "sem_A(x) = x⇒",
    "NS_B_True":   "sem_B(true) = true̅",
    "NS_B_False":  "sem_B(false) = false̅",
    "NS_B_Neg":    "sem_B(not b) = S^1(neg, sem_B(b))",
    "NS_B_And":    "sem_B(b1 and b2) = S^2(and, sem_B(b1), sem_B(b2))",
    "NS_B_Or":     "sem_B(b1 or b2) = S^2(or, sem_B(b1), sem_B(b2))",
}
for _op, _rule in ARITH_RULE.items():
    RULE_TEXT[_rule] = f"sem_A(a1 {_op} a2) = S^2({ARITH_FN[_op]}, sem_A(a1), sem_A(a2))"
for _op, _rule in CMP_RULE.items():
    RULE_TEXT[_rule] = f"sem_B(a1 {_op} a2) = S^2({CMP_FN[_op]}, sem_A(a1), sem_A(a2))"


def rule_of(n: A.Node) -> str:
    if isinstance(n, A.Program):
        return "NS_Prog"
    if isinstance(n, A.Seq):
        return "NS_Stm_Seq"
    if isinstance(n, A.Assign):
        return "NS_Stm_As"
    if isinstance(n, A.If):
        return "NS_Stm_If"
    if isinstance(n, A.While):
        return "NS_Stm_Wh"
    if isinstance(n, A.Block):
        return "NS_Stm_BE"
    if isinstance(n, A.Skip):
        return "NS_Stm_skip"
    if isinstance(n, A.Num):
        return "NS_A_Num"
    if isinstance(n, A.Var):
        return "NS_A_Var"
    if isinstance(n, A.BinOp):
        return ARITH_RULE[n.op]
    if isinstance(n, A.Compare):
        return CMP_RULE[n.op]
    if isinstance(n, A.BoolConst):
        return "NS_B_True" if n.value else "NS_B_False"
    if isinstance(n, A.Not):
        return "NS_B_Neg"
    if isinstance(n, A.BoolOp):
        return "NS_B_And" if n.op == "and" else "NS_B_Or"
    raise TypeError(type(n).__name__)


def build(n: A.Node, sub=None) -> Term:
    """AST -> терм. sub(child) дозволяє підставити замість дитини щось своє
    (так пояснення показує sem_S(...) для вкладених операторів)."""
    s = sub or build
    if isinstance(n, (A.Program, A.Block)):
        return s(n.body)
    if isinstance(n, A.Seq):
        return Comp(s(n.first), s(n.second))
    if isinstance(n, A.Assign):
        return AS(n.var, s(n.expr))
    if isinstance(n, A.If):
        return IF(s(n.cond), s(n.then), s(n.else_))
    if isinstance(n, A.While):
        return WH(s(n.cond), s(n.body))
    if isinstance(n, A.Skip):
        return Id()
    if isinstance(n, A.Num):
        return Const(n.value)
    if isinstance(n, A.Var):
        return Deref(n.name)
    if isinstance(n, A.BinOp):
        return Sup(ARITH_FN[n.op], (s(n.left), s(n.right)))
    if isinstance(n, A.Compare):
        return Sup(CMP_FN[n.op], (s(n.left), s(n.right)))
    if isinstance(n, A.BoolConst):
        return Const(n.value)
    if isinstance(n, A.Not):
        return Sup(BOOL_FN["not"], (s(n.operand),))
    if isinstance(n, A.BoolOp):
        return Sup(BOOL_FN[n.op], (s(n.left), s(n.right)))
    raise TypeError(type(n).__name__)


def build_term(program: A.Node) -> Term:
    return build(program)


# ---------- покрокове пояснення ----------

@dataclass(frozen=True)
class Placeholder(Term):
    """sem_S(фрагмент) - ще не розкритий вкладений оператор"""
    text: str


def fragment(n: A.Node, source: str, limit: int = 40) -> str:
    """Текст оператора для запису sem_S(...). Довгі if/while скорочую до заголовка."""
    s = " ".join(n.span.text(source).split())
    if len(s) <= limit:
        return s
    if isinstance(n, A.If):
        return f"if {fragment(n.cond, source)} then ..."
    if isinstance(n, A.While):
        return f"while {fragment(n.cond, source)} do ..."
    return s[:limit - 3].rstrip() + "..."


@dataclass
class ExplainStep:
    rules: list[str]
    lhs: str          # sem_S(фрагмент)
    rhs: str          # терм, де вкладені if/while ще записані як sem_S(...)
    span: dict

    def text(self) -> str:
        return ", ".join(self.rules) + ":\n" + f"{self.lhs} = {self.rhs}"

    def to_dict(self) -> dict:
        return {"rules": self.rules, "lhs": self.lhs, "rhs": self.rhs, "span": self.span}


def is_compound(n: A.Node) -> bool:
    # такі оператори пояснюю окремим кроком, решту розкриваю одразу на місці
    return isinstance(n, (A.If, A.While))


def explain(program: A.Program, source: str, fmt: str = "text") -> list[ExplainStep]:
    """Кроки як у практичній 2. Послідовності, begin-end, присвоєння, skip і вирази
    розкриваються одразу; вкладені if і while пишуться як sem_S(...) і розкриваються
    наступними кроками."""
    steps = []

    def visit(n: A.Node, lhs: str):
        rules = []
        later = []

        def sub(c: A.Node) -> Term:
            if is_compound(c):
                later.append(c)
                return Placeholder(f"sem_S({fragment(c, source)})")
            r = rule_of(c)
            if r not in rules:
                rules.append(r)
            return build(c, sub)

        rules.append(rule_of(n))
        term = build(n, sub)
        steps.append(ExplainStep(rules, lhs, render_with_placeholders(term, fmt),
                                 n.span.to_dict()))
        for c in later:
            visit(c, f"sem_S({fragment(c, source)})")

    visit(program, "sem_P(P)")
    return steps


def render_with_placeholders(t: Term, fmt: str) -> str:
    # render() не знає про Placeholder, тому підміняю його тимчасово на змінну з таким ім'ям
    if isinstance(t, Placeholder):
        return t.text
    marks = {}

    def swap(x):
        if isinstance(x, Placeholder):
            key = f"\x00{len(marks)}\x00"
            marks[key] = x.text
            return Deref(key)
        if isinstance(x, Comp):
            return Comp(swap(x.first), swap(x.second))
        if isinstance(x, IF):
            return IF(swap(x.cond), swap(x.then), swap(x.else_))
        if isinstance(x, WH):
            return WH(swap(x.cond), swap(x.body))
        return x

    s = render(swap(t), fmt)
    arrow = {"latex": r"\Rightarrow", "ascii": "=>"}.get(fmt, "⇒")
    for key, text in marks.items():
        s = s.replace(key + arrow, text)
    return s
