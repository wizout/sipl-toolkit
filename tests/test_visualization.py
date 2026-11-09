import json
import shutil

import pytest

from sipl import parse_tree
from sipl.visualization import to_dict, to_dot, to_json, to_svg, to_text

from conftest import ROOT

SRC = (ROOT / "examples" / "ok" / "prime.sipl").read_text(encoding="utf-8")


def test_text_tree_has_numbered_leaves():
    t = to_text(parse_tree(SRC), SRC)
    assert t.startswith("<програма>   [P]")
    assert "Всього листків: 44" in t
    assert "1 begin 2 if 3 N 4 > 5 1" in t


def test_json_nodes_linked_to_source():
    d = json.loads(to_json(parse_tree(SRC), SRC))
    assert d["symbol"] == "<програма>" and d["rule"] == "P"
    assert d["bnf"] == "<програма> ::= begin <оператор> end"
    first_if = d["children"][1]["children"][0]["children"][0]
    assert first_if["rule"] == "S_If"
    assert first_if["text"] == "if N > 1 then R := 1 else R := 0"
    assert first_if["span"]["line"] == 3
    leaf = first_if["children"][0]
    assert leaf == {"symbol": "if", "span": leaf["span"], "text": "if", "leaf": 2, "token": "kw"}


def test_dot():
    dot = to_dot(parse_tree(SRC), SRC)
    assert dot.startswith("digraph ParseTree {") and dot.rstrip().endswith("}")
    assert dot.count("->") == len([l for l in dot.splitlines() if "[label" in l]) - 1
    assert 'tooltip="3:5: if N &gt; 1 then R := 1 else R := 0 (S_If)"' in dot
    assert "<B>while</B>" in dot


@pytest.mark.skipif(not shutil.which("dot"), reason="Graphviz не встановлено")
def test_svg():
    assert "<svg" in to_svg(parse_tree(SRC), SRC)


def test_svg_without_graphviz(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        to_svg(parse_tree(SRC), SRC)


def test_to_dict_small():
    d = to_dict(parse_tree("begin skip end"), "begin skip end")
    assert [c["symbol"] for c in d["children"]] == ["begin", "<оператор>", "end"]
