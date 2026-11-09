import pytest

from sipl import ast as A
from sipl import parse, parse_tree
from sipl.errors import SiplSyntaxError
from sipl.lexer import tokenize

from conftest import BAD, OK

PRIME = (OK[0].parent / "prime.sipl").read_text(encoding="utf-8")


@pytest.mark.parametrize("path", OK, ids=lambda p: p.name)
def test_ok_examples_parse(path):
    assert isinstance(parse(path.read_text(encoding="utf-8")), A.Program)


@pytest.mark.parametrize("path", BAD, ids=lambda p: p.name)
def test_bad_examples_fail_with_position(path):
    with pytest.raises(SiplSyntaxError) as e:
        parse(path.read_text(encoding="utf-8"))
    assert e.value.span is not None
    assert "рядок" in str(e.value)


def test_counts():
    # критерій CORE-01: щонайменше 10 правильних і 10 неправильних прикладів
    assert len(OK) >= 10 and len(BAD) >= 10


def test_seq_is_left_associative():
    p = parse("begin A := 1; B := 2; C := 3 end")
    assert isinstance(p.body, A.Seq)
    assert isinstance(p.body.first, A.Seq)          # (A; B); C
    assert p.body.second.var == "C"


def test_while_binds_tighter_than_semicolon():
    p = parse("begin while X > 0 do X := X - 1; Y := 5 end")
    assert isinstance(p.body, A.Seq)
    assert isinstance(p.body.first, A.While)
    assert isinstance(p.body.first.body, A.Assign)


def test_arith_priority_and_parens():
    e = parse("begin X := 1 + 2 * 3 end").body.expr
    assert e.op == "+" and e.right.op == "*"
    e = parse("begin X := (1 + 2) * 3 end").body.expr
    assert e.op == "*" and e.left.op == "+"
    e = parse("begin X := 10 - 3 - 2 end").body.expr
    assert e.left.op == "-"                          # (10 - 3) - 2


def test_bool_priority():
    c = parse("begin if not X > 1 or Y = 2 and true then skip else skip end").body.cond
    assert c.op == "or" and isinstance(c.left, A.Not) and c.right.op == "and"


def test_paren_condition_vs_paren_expression():
    c = parse("begin if (X + 1) > 2 then skip else skip end").body.cond
    assert isinstance(c, A.Compare) and c.left.op == "+"
    c = parse("begin if (X > 1) and (Y < 2) then skip else skip end").body.cond
    assert c.op == "and"


def test_spans_point_to_source():
    src = "begin\n  X := 1;\n  Y := X + 2\nend"
    p = parse(src)
    y = p.body.second
    assert (y.span.line, y.span.col) == (3, 3)
    assert y.span.text(src) == "Y := X + 2"
    assert y.expr.span.text(src) == "X + 2"


def test_parse_tree_leaves_give_back_program():
    # як у практичній 1: листки дерева зліва направо = текст програми
    tree = parse_tree(PRIME)
    leaves = [l.token.value for l in tree.leaves()]
    tokens = [t.value for t in tokenize(PRIME) if t.kind != "eof"]
    assert leaves == tokens
    assert len(leaves) == 44


def test_parse_tree_rules():
    tree = parse_tree("begin X := 1; Y := 2 end")
    assert tree.symbol == "<програма>" and tree.rule == "P"
    assert tree.children[1].rule == "S_Seq"


@pytest.mark.parametrize("src, piece", [
    ("begin X := 1 Y := 2 end", "потрібна ';'"),
    ("begin X := 1; end", "зайва ';'"),
    ("begin X = 1 end", "':='"),
    ("begin if X > 0 then skip end", "else"),
    ("begin X := 1", "'end'"),
    ("X := 1", "begin"),
    ("begin X := 1 end end", "зайвий текст"),
    ("begin X := @ end", "невідомий символ"),
    ("begin if (X > 1 then skip else skip end", "')'"),
])
def test_error_messages(src, piece):
    with pytest.raises(SiplSyntaxError) as e:
        parse(src)
    assert piece in e.value.message


def test_error_line_and_column():
    with pytest.raises(SiplSyntaxError) as e:
        parse("begin\n  X := 1\n  Y := 2\nend")
    assert (e.value.span.line, e.value.span.col) == (3, 3)


def test_ast_to_dict():
    d = parse("begin X := 1 end").to_dict()
    assert d["node"] == "Program" and d["body"]["node"] == "Assign"
    assert d["body"]["span"]["line"] == 1
