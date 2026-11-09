import pytest

from sipl import parse, run
from sipl.semantics import build_term, evaluate, explain
from sipl.semantics.terms import AS, IF, WH, Comp, Const, Deref, Id, Sup, render, to_dict

from conftest import OK, ROOT

GOLDEN = ROOT / "tests" / "golden"

# терм з практичної 2 (варіант 15), риска над константою - комбінований символ U+0305
PRACTICAL_2 = ("(IF(S^2(gr, N⇒, 1̅), AS^R(1̅), AS^R(0̅)) · AS^D(2̅)) · "
               "WH(S^2(gr, N⇒, D⇒), IF(S^2(eq, S^2(mod, N⇒, D⇒), 0̅), AS^R(0̅), id) · "
               "AS^D(S^2(add, D⇒, 1̅)))")


def src(name):
    return (ROOT / "examples" / "ok" / name).read_text(encoding="utf-8")


def test_term_matches_practical_2():
    assert render(build_term(parse(src("prime.sipl")))) == PRACTICAL_2


@pytest.mark.parametrize("path", OK, ids=lambda p: p.name)
def test_golden_terms(path):
    t = build_term(parse(path.read_text(encoding="utf-8")))
    assert render(t) + "\n" == (GOLDEN / f"{path.stem}.term").read_text(encoding="utf-8")
    assert render(t, "latex") + "\n" == (GOLDEN / f"{path.stem}.tex").read_text(encoding="utf-8")


def test_all_operators():
    t = build_term(parse(
        "begin X := (A + B) - C * D div E mod F; "
        "if not (A < B) and A <= B or A <> B and A >= B then skip else skip end"))
    s = render(t, "ascii")
    for fn in ["add", "sub", "mult", "div", "mod", "ls", "leq", "neq", "geq",
               "and", "or", "neg"]:
        assert f"({fn}," in s
    assert "S^1(neg" in s and "id" in s


def test_term_structure():
    t = build_term(parse("begin while X > 0 do begin X := X - 1 end; Y := 1 end"))
    assert t == Comp(WH(Sup("gr", (Deref("X"), Const(0))),
                        AS("X", Sup("sub", (Deref("X"), Const(1))))),
                     AS("Y", Const(1)))
    assert build_term(parse("begin skip end")) == Id()


def test_render_formats():
    t = IF(Sup("eq", (Deref("X"), Const(10))), AS("Y", Const(True)), Id())
    assert render(t, "ascii") == "IF(S^2(eq, X=>, ~10), AS^Y(~true), id)"
    assert r"\overline{10}" in render(t, "latex")
    assert to_dict(t)["term"] == "IF"


def test_explain_like_practical_2():
    s = src("prime.sipl")
    steps = explain(parse(s), s)
    assert steps[0].lhs == "sem_P(P)"
    assert steps[0].rules[:2] == ["NS_Prog", "NS_Stm_Seq"]
    assert steps[0].rhs == ("(sem_S(if N > 1 then R := 1 else R := 0) · AS^D(2̅)) · "
                            "sem_S(while N > D do ...)")
    assert steps[1].rhs == "IF(S^2(gr, N⇒, 1̅), AS^R(1̅), AS^R(0̅))"
    assert "NS_A_Mod" in steps[3].rules
    assert len(steps) == 4


# ---------- обчислення терму ----------

def test_eval_prime_3_like_practical_2():
    res = evaluate(build_term(parse(src("prime.sipl"))), {"N": 3})
    assert res.state == {"N": 3, "R": 1, "D": 3}
    text = res.text()
    assert "gr(N⇒(st), 1̅(st)) = gr(3, 1) = true" in text
    assert "eq(mod(3, 2), 0) = eq(1, 0) = false" in text
    assert "st₂∇[D ↦ add(2, 1)] = st₂∇[D ↦ 3]" in text
    assert text.count("Ітерація") == 1
    assert text + "\n" == (GOLDEN / "prime_N3.eval").read_text(encoding="utf-8")


@pytest.mark.parametrize("name, state", [
    ("prime.sipl", {"N": 12}), ("power.sipl", {"X": 3, "Y": 4}),
    ("gcd.sipl", {"X": 21, "Y": 6}), ("fib.sipl", {"N": 7}),
    ("bool_ops.sipl", {"X": 3}), ("sum_digits.sipl", {"N": 405}),
    ("divisible.sipl", {"X": 9, "Y": 3}), ("max3.sipl", {"A": 1, "B": 5, "C": 2}),
])
def test_term_agrees_with_interpreter(name, state):
    p = parse(src(name))
    assert evaluate(build_term(p), state).state == run(p, state)[0]


def test_undefined_variable():
    res = evaluate(build_term(parse(src("prime.sipl"))), {})
    assert res.state is None and "N" in res.undefined
    assert "⊥" in res.text()


def test_undefined_division():
    res = evaluate(build_term(parse("begin X := 5 mod Y end")), {"Y": 0})
    assert res.state is None and "ділення на нуль" in res.undefined


def test_undefined_infinite_loop():
    res = evaluate(build_term(parse(src("loop_forever.sipl"))), {}, max_iterations=5)
    assert res.state is None and "5" in res.undefined
    assert res.text().count("Ітерація") == 5


def test_eval_ascii_and_json():
    res = evaluate(build_term(parse("begin X := X + 1 end")), {"X": 1}, fmt="ascii")
    assert "st <| [X -> add(X=>(st), ~1(st))]" in res.text()
    d = res.to_dict()
    assert d["defined"] and d["state"] == {"X": 2} and d["steps"][0]["kind"] == "step"


def test_eval_expression_term():
    res = evaluate(Sup("add", (Deref("X"), Const(2))), {"X": 5})
    assert res.value == 7 and "add(5, 2) = 7" in res.text()


@pytest.mark.parametrize("path", OK, ids=lambda p: p.name)
def test_explain_covers_every_example(path):
    s = path.read_text(encoding="utf-8")
    steps = explain(parse(s), s, "ascii")
    used = {r for st in steps for r in st.rules}
    # кожне правило з кроків справді є в таблиці правил
    from sipl.semantics import RULE_TEXT
    assert used <= set(RULE_TEXT)
    assert steps[0].lhs == "sem_P(P)"


def test_explain_bool_rules():
    s = "begin if not (A < B) and true or false then X := A div 2 else skip end"
    rules = explain(parse(s), s)[1].rules
    for r in ["NS_B_Or", "NS_B_And", "NS_B_Neg", "NS_B_ls", "NS_B_True", "NS_B_False",
              "NS_A_Div", "NS_Stm_skip"]:
        assert r in rules
