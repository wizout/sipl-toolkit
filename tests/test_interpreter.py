import math

import pytest

from sipl import parse, run
from sipl.errors import SiplRuntimeError
from sipl.interpreter import apply_arith

from conftest import ROOT


def prog(name):
    return parse((ROOT / "examples" / "ok" / name).read_text(encoding="utf-8"))


def is_prime(n):
    return n > 1 and all(n % d for d in range(2, n))


@pytest.mark.parametrize("n", range(1, 40))
def test_prime(n):
    st, _ = run(prog("prime.sipl"), {"N": n})
    assert st["R"] == int(is_prime(n))


@pytest.mark.parametrize("x, y", [(2, 0), (2, 10), (3, 4), (1, 7)])
def test_power(x, y):
    assert run(prog("power.sipl"), {"X": x, "Y": y})[0]["R"] == x ** y


@pytest.mark.parametrize("n", range(0, 8))
def test_factorial_and_double_factorial(n):
    assert run(prog("factorial.sipl"), {"N": n})[0]["R"] == math.factorial(n)
    assert run(prog("double_factorial.sipl"), {"N": n})[0]["R"] == 2 ** n * math.factorial(n)


@pytest.mark.parametrize("x, y", [(12, 18), (7, 7), (35, 14), (1, 9)])
def test_gcd(x, y):
    assert run(prog("gcd.sipl"), {"X": x, "Y": y})[0]["R"] == math.gcd(x, y)


@pytest.mark.parametrize("x, y", [(12, 4), (13, 4), (4, 4), (3, 5)])
def test_divisible(x, y):
    assert run(prog("divisible.sipl"), {"X": x, "Y": y})[0]["R"] == int(x % y == 0)


def test_other_examples():
    assert run(prog("sum_digits.sipl"), {"N": 9075})[0]["S"] == 21
    assert run(prog("fib.sipl"), {"N": 10})[0]["R"] == 55
    assert run(prog("max3.sipl"), {"A": 3, "B": 9, "C": 5})[0]["M"] == 9
    assert run(prog("skip_only.sipl"), {"Q": 1})[0] == {"Q": 1}
    assert run(prog("nested_blocks.sipl"))[0] == {"X": 1, "Y": 9}
    st, _ = run(prog("bool_ops.sipl"), {"X": 4})
    assert st == {"X": 4, "R": 1, "Z": 7, "W": 2}
    st, _ = run(prog("bool_ops.sipl"), {"X": 11})
    assert st["R"] == 0 and st["W"] == 1


def test_input_state_is_not_changed():
    start = {"N": 5}
    run(prog("prime.sipl"), start)
    assert start == {"N": 5}


def test_infinite_loop_is_stopped():
    with pytest.raises(SiplRuntimeError) as e:
        run(prog("loop_forever.sipl"), max_steps=1000)
    assert "1000" in e.value.message and e.value.span.line == 4


def test_unknown_variable():
    with pytest.raises(SiplRuntimeError) as e:
        run(parse("begin X := Y + 1 end"))
    assert "Y" in e.value.message and e.value.span.col == 12


def test_division_by_zero():
    with pytest.raises(SiplRuntimeError):
        run(parse("begin X := 5 div 0 end"))
    with pytest.raises(SiplRuntimeError):
        run(parse("begin X := 5 mod (2 - 2) end"))


def test_arith():
    assert apply_arith("div", 7, 2) == 3 and apply_arith("mod", 7, 2) == 1
    assert apply_arith("-", 2, 5) == -3


def test_trace_events():
    st, it = run(parse("begin X := 2; while X > 0 do X := X - 1 end"), trace=True)
    kinds = [e.event for e in it.trace]
    assert kinds == ["assign", "cond", "assign", "cond", "assign", "cond", "finish"]
    assert it.trace[-1].to_dict()["state"] == {"X": 0}
    assert [e.detail["value"] for e in it.trace if e.event == "cond"] == [True, True, False]
