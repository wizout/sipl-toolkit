"""Перевіряю, що формальна граматика grammar/sipl.lark і парсер погоджуються:
однакові програми приймаються/відкидаються і дають однакову структуру."""
import pytest

lark = pytest.importorskip("lark")

from sipl import ast as A
from sipl import parse
from sipl.errors import SiplSyntaxError

from conftest import BAD, OK, ROOT

GRAMMAR = lark.Lark((ROOT / "grammar" / "sipl.lark").read_text(encoding="utf-8"),
                    parser="earley")

LARK_NAMES = {"add": "+", "sub": "-", "mult": "*", "div": "div", "mod": "mod",
              "or_": "or", "and_": "and"}


def from_lark(t):
    if isinstance(t, lark.Token):
        return int(t) if t.type == "NUMBER" else str(t)
    k, ch = t.data, [from_lark(c) for c in t.children]
    if k == "program":
        return ch[0]
    if k in LARK_NAMES:
        return (LARK_NAMES[k], ch[0], ch[1])
    if k == "cmp":
        return (ch[1], ch[0], ch[2])
    if k in ("true", "false"):
        return k == "true"
    if k in ("num", "var"):
        return ch[0]
    return (k.rstrip("_"), *ch)


def from_ast(n):
    if isinstance(n, A.Program):
        return from_ast(n.body)
    if isinstance(n, A.Num):
        return n.value
    if isinstance(n, A.Var):
        return n.name
    if isinstance(n, A.BoolConst):
        return n.value
    if isinstance(n, (A.BinOp, A.Compare, A.BoolOp)):
        return (n.op, from_ast(n.left), from_ast(n.right))
    if isinstance(n, A.Not):
        return ("not", from_ast(n.operand))
    if isinstance(n, A.Assign):
        return ("assign", n.var, from_ast(n.expr))
    if isinstance(n, A.Seq):
        return ("seq", from_ast(n.first), from_ast(n.second))
    if isinstance(n, A.If):
        return ("if", from_ast(n.cond), from_ast(n.then), from_ast(n.else_))
    if isinstance(n, A.While):
        return ("while", from_ast(n.cond), from_ast(n.body))
    if isinstance(n, A.Block):
        return ("block", from_ast(n.body))
    if isinstance(n, A.Skip):
        return ("skip",)
    raise TypeError(n)


@pytest.mark.parametrize("path", OK, ids=lambda p: p.name)
def test_grammar_accepts_and_matches_parser(path):
    src = path.read_text(encoding="utf-8")
    assert from_lark(GRAMMAR.parse(src)) == from_ast(parse(src))


@pytest.mark.parametrize("path", BAD, ids=lambda p: p.name)
def test_grammar_rejects(path):
    src = path.read_text(encoding="utf-8")
    with pytest.raises(lark.exceptions.LarkError):
        GRAMMAR.parse(src)
    with pytest.raises(SiplSyntaxError):
        parse(src)
