import json
import os
import subprocess
import sys

import pytest

from sipl.cli import EXIT_FILE, EXIT_SYNTAX, EXIT_UNDEFINED, EXIT_USAGE, main

from conftest import ROOT

OK = str(ROOT / "examples" / "ok")
BAD = str(ROOT / "examples" / "bad")


def call(capsys, *args):
    code = main(list(args))
    o = capsys.readouterr()
    return code, o.out, o.err


def test_check(capsys):
    assert call(capsys, "check", f"{OK}/prime.sipl")[:2] == (0, "Синтаксис правильний.\n")
    code, _, err = call(capsys, "check", f"{BAD}/missing_semicolon.sipl")
    assert code == EXIT_SYNTAX and "рядок 3, колонка 5" in err and "^" in err


def test_check_json(capsys):
    code, out, _ = call(capsys, "check", f"{BAD}/no_end.sipl", "--json")
    d = json.loads(out)
    assert code == EXIT_SYNTAX and d["ok"] is False and d["error"]["kind"] == "syntax"
    assert d["error"]["span"]["line"] == 2


def test_parse(capsys):
    code, out, _ = call(capsys, "parse", f"{OK}/power.sipl")
    assert code == 0 and out.startswith("Program") and "BinOp *" in out
    code, out, _ = call(capsys, "parse", f"{OK}/power.sipl", "--json")
    assert json.loads(out)["ast"]["node"] == "Program"


def test_run(capsys):
    code, out, _ = call(capsys, "run", f"{OK}/power.sipl", "-s", "X=2", "--set", "Y=5")
    assert code == 0 and "R = 32" in out
    code, out, _ = call(capsys, "run", f"{OK}/power.sipl", "-s", "X=2", "-s", "Y=1",
                        "--json", "--trace")
    d = json.loads(out)
    assert d["state"]["R"] == 2 and d["trace"][-1]["event"] == "finish"
    code, out, _ = call(capsys, "run", f"{OK}/factorial.sipl", "-s", "N=3", "--trace")
    assert "N := 2" in out and "умова while: false" in out


def test_run_errors(capsys):
    assert call(capsys, "run", f"{OK}/loop_forever.sipl", "--max-steps", "10")[0] == EXIT_UNDEFINED
    assert call(capsys, "run", f"{OK}/power.sipl")[0] == EXIT_UNDEFINED     # X, Y не задані
    assert call(capsys, "run", f"{OK}/power.sipl", "-s", "X")[0] == EXIT_USAGE
    assert call(capsys, "run", f"{OK}/power.sipl", "-s", "X=a")[0] == EXIT_USAGE
    assert call(capsys, "run", f"{OK}/power.sipl", "-s", "1X=2")[0] == EXIT_USAGE
    assert call(capsys, "run", f"{OK}/nope.sipl")[0] == EXIT_FILE
    with pytest.raises(SystemExit) as e:
        main(["fly", "x"])
    assert e.value.code == EXIT_USAGE


def test_tree(capsys, tmp_path):
    code, out, _ = call(capsys, "tree", f"{OK}/prime.sipl")
    assert code == 0 and "Всього листків: 44" in out
    assert json.loads(call(capsys, "tree", f"{OK}/prime.sipl", "-f", "json")[1])["rule"] == "P"
    assert call(capsys, "tree", f"{OK}/prime.sipl", "-f", "dot")[1].startswith("digraph")
    f = tmp_path / "t.dot"
    call(capsys, "tree", f"{OK}/prime.sipl", "-f", "dot", "-o", str(f))
    assert f.read_text(encoding="utf-8").startswith("digraph")


def test_tree_svg_without_graphviz(capsys, monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert call(capsys, "tree", f"{OK}/prime.sipl", "-f", "svg")[0] == EXIT_USAGE


def test_term(capsys):
    code, out, _ = call(capsys, "term", f"{OK}/prime.sipl")
    assert code == 0 and out.startswith("(IF(S^2(gr, N⇒")
    assert "~1" in call(capsys, "term", f"{OK}/prime.sipl", "-f", "ascii")[1]
    out = call(capsys, "term", f"{OK}/prime.sipl", "--explain")[1]
    assert "NS_Prog" in out and "Терм програми" in out
    d = json.loads(call(capsys, "term", f"{OK}/prime.sipl", "--json", "--explain")[1])
    assert d["tree"]["term"] == "Comp" and len(d["steps"]) == 4


def test_eval(capsys):
    code, out, _ = call(capsys, "eval", f"{OK}/prime.sipl", "-s", "N=3")
    assert code == 0 and "Результат: st₃ = [N ↦ 3, R ↦ 1, D ↦ 3]" in out
    code, out, _ = call(capsys, "eval", f"{OK}/prime.sipl", "--json")
    assert code == EXIT_UNDEFINED and json.loads(out)["defined"] is False
    code, out, _ = call(capsys, "eval", f"{OK}/power.sipl", "-s", "X=2", "-s", "Y=1", "--ascii")
    assert code == 0 and "->" in out and "↦" not in out


def test_rules(capsys):
    code, out, _ = call(capsys, "rules")
    assert code == 0 and "NS_Stm_Wh" in out and "AF_WH" in out
    assert "AF" in json.loads(call(capsys, "rules", "--json")[1])


def test_stdin(capsys, monkeypatch):
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO("begin X := 2 end"))
    assert "X = 2" in call(capsys, "run", "-")[1]


def test_python_m_sipl():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    r = subprocess.run([sys.executable, "-m", "sipl", "run", f"{OK}/gcd.sipl",
                        "-s", "X=12", "-s", "Y=18"], capture_output=True, text=True,
                       encoding="utf-8", env=env)
    assert r.returncode == 0 and "R = 6" in r.stdout
