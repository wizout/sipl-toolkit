"""Абстрактне синтаксичне дерево (AST) мови SIPL.

На відміну від дерева виводу, тут немає дужок, ключових слів і крапок з комою,
тільки сама структура програми. Кожен вузол пам'ятає свій span у тексті.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

from .errors import SourceSpan


@dataclass
class Node:
    span: SourceSpan = field(repr=False, compare=False)

    def children(self) -> list["Node"]:
        return [getattr(self, f.name) for f in fields(self)
                if isinstance(getattr(self, f.name), Node)]

    def to_dict(self) -> dict:
        d = {"node": type(self).__name__, "span": self.span.to_dict()}
        for f in fields(self):
            if f.name == "span":
                continue
            v = getattr(self, f.name)
            d[f.name] = v.to_dict() if isinstance(v, Node) else v
        return d


# ---------- арифметичні вирази ----------

@dataclass
class Num(Node):
    value: int


@dataclass
class Var(Node):
    name: str


@dataclass
class BinOp(Node):
    op: str          # "+", "-", "*", "div", "mod"
    left: Node
    right: Node


# ---------- умови ----------

@dataclass
class BoolConst(Node):
    value: bool


@dataclass
class Compare(Node):
    op: str          # "<", "<=", "=", "<>", ">", ">="
    left: Node
    right: Node


@dataclass
class Not(Node):
    operand: Node


@dataclass
class BoolOp(Node):
    op: str          # "and", "or"
    left: Node
    right: Node


# ---------- оператори ----------

@dataclass
class Assign(Node):
    var: str
    expr: Node


@dataclass
class Seq(Node):
    first: Node
    second: Node


@dataclass
class If(Node):
    cond: Node
    then: Node
    else_: Node


@dataclass
class While(Node):
    cond: Node
    body: Node


@dataclass
class Block(Node):
    """begin S end всередині програми"""
    body: Node


@dataclass
class Skip(Node):
    pass


@dataclass
class Program(Node):
    body: Node


ARITH = (Num, Var, BinOp)
BOOL = (BoolConst, Compare, Not, BoolOp)
STMT = (Assign, Seq, If, While, Block, Skip)
