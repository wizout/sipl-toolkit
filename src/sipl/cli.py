"""Командний рядок: sipl <команда> файл.sipl [опції]

  check  перевірити синтаксис
  parse  показати AST
  run    виконати програму (інтерпретатор)
  tree   дерево синтаксичного виводу: text | json | dot | svg
  term   семантичний терм: text | ascii | latex | json, з --explain покроково
  eval   обчислити терм на стані з поясненням кожного переходу
  rules  список правил NS_* та AF_*

Коди завершення: 0 - все добре, 1 - синтаксична помилка, 2 - неправильні аргументи,
3 - програма невизначена на цьому стані (ділення на 0, невідома змінна, ліміт кроків),
4 - файл не знайдено або не читається.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .errors import SiplError, SiplRuntimeError, SiplSyntaxError
from .interpreter import DEFAULT_MAX_STEPS, run
from .parser import parse_tree, to_ast

EXIT_OK, EXIT_SYNTAX, EXIT_USAGE, EXIT_UNDEFINED, EXIT_FILE = 0, 1, 2, 3, 4


def ast_text(node, indent=0) -> str:
    from . import ast as A
    pad = "  " * indent
    name = type(node).__name__
    extra = ""
    if isinstance(node, A.Num):
        extra = f" {node.value}"
    elif isinstance(node, A.Var):
        extra = f" {node.name}"
    elif isinstance(node, (A.BinOp, A.Compare, A.BoolOp)):
        extra = f" {node.op}"
    elif isinstance(node, A.Assign):
        extra = f" {node.var}"
    elif isinstance(node, A.BoolConst):
        extra = f" {str(node.value).lower()}"
    lines = [f"{pad}{name}{extra}   {node.span}"]
    for c in node.children():
        lines.append(ast_text(c, indent + 1))
    return "\n".join(lines)


def parse_state(pairs: list[str]) -> dict:
    st = {}
    for p in pairs:
        if "=" not in p:
            raise ValueError(f"'{p}': значення задається як ІМ'Я=ЧИСЛО, наприклад N=5")
        k, v = p.split("=", 1)
        k = k.strip()
        if not (k.replace("_", "a").isalnum() and not k[0].isdigit()):
            raise ValueError(f"'{k}' не схоже на ім'я змінної")
        try:
            st[k] = int(v)
        except ValueError:
            raise ValueError(f"'{v}' не ціле число (змінна {k})") from None
    return st


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sipl", description="Інструменти для мови SIPL")
    ap.add_argument("--version", action="version", version=f"sipl {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name, help_):
        p = sub.add_parser(name, help=help_)
        if name != "rules":
            p.add_argument("file", help="файл з програмою SIPL ('-' - читати зі stdin)")
        p.add_argument("--json", action="store_true", help="вивід у JSON")
        return p

    cmd("check", "перевірити синтаксис")
    cmd("parse", "показати AST")
    p = cmd("run", "виконати програму")
    p.add_argument("--set", "-s", action="append", default=[], metavar="X=N",
                   help="початкове значення змінної, можна кілька разів")
    p.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    p.add_argument("--trace", action="store_true", help="показати події виконання")
    p = cmd("tree", "дерево синтаксичного виводу")
    p.add_argument("--format", "-f", choices=["text", "json", "dot", "svg"], default="text")
    p.add_argument("--output", "-o", help="записати у файл замість екрану")
    p = cmd("term", "семантичний терм програми")
    p.add_argument("--format", "-f", choices=["text", "ascii", "latex"], default="text")
    p.add_argument("--explain", action="store_true", help="покроково, за правилами NS_*")
    p = cmd("eval", "обчислити терм на стані")
    p.add_argument("--set", "-s", action="append", default=[], metavar="X=N")
    p.add_argument("--ascii", action="store_true", help="без юнікод-символів")
    p.add_argument("--max-iterations", type=int, default=1000)
    cmd("rules", "правила побудови і обчислення термів")
    return ap


def read_source(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")      # щоб на Windows не ламались ⇒, ↦
        except (AttributeError, ValueError):
            pass

    args = build_argparser().parse_args(argv)
    as_json = args.json

    def out(obj_or_text):
        print(json.dumps(obj_or_text, ensure_ascii=False, indent=2)
              if as_json else obj_or_text)

    def fail(code, err: SiplError | str, source: str | None = None):
        if as_json:
            e = err.to_dict() if isinstance(err, SiplError) else {"kind": "error",
                                                                  "message": str(err)}
            out({"ok": False, "error": e})
        else:
            print(f"Помилка: {err}", file=sys.stderr)
            if isinstance(err, SiplError) and err.span and source is not None:
                line = source.splitlines()[err.span.line - 1] if source.splitlines() else ""
                print("  " + line, file=sys.stderr)
                print("  " + " " * (err.span.col - 1) + "^", file=sys.stderr)
        return code

    if args.cmd == "rules":
        from .semantics.build import RULE_TEXT
        from .semantics.evaluate import AF_TEXT
        if as_json:
            out({"NS": RULE_TEXT, "AF": AF_TEXT})
        else:
            out("Побудова терму (NS_*):\n" +
                "\n".join(f"  {k:12} {v}" for k, v in RULE_TEXT.items()) +
                "\n\nОбчислення терму на стані (AF_*):\n" +
                "\n".join(f"  {k:12} {v}" for k, v in AF_TEXT.items()))
        return EXIT_OK

    try:
        source = read_source(args.file)
    except OSError as e:
        return fail(EXIT_FILE, f"не вдалось прочитати файл {args.file}: {e.strerror}")

    try:
        tree = parse_tree(source)
    except SiplSyntaxError as e:
        return fail(EXIT_SYNTAX, e, source)
    program = to_ast(tree)

    try:
        st = parse_state(getattr(args, "set", []))
    except ValueError as e:
        return fail(EXIT_USAGE, str(e))

    if args.cmd == "check":
        out({"ok": True} if as_json else "Синтаксис правильний.")
        return EXIT_OK

    if args.cmd == "parse":
        out({"ok": True, "ast": program.to_dict()} if as_json else ast_text(program))
        return EXIT_OK

    if args.cmd == "run":
        try:
            final, it = run(program, st, max_steps=args.max_steps, trace=args.trace)
        except SiplRuntimeError as e:
            return fail(EXIT_UNDEFINED, e, source)
        if as_json:
            res = {"ok": True, "state": final, "steps": it.steps}
            if args.trace:
                res["trace"] = [ev.to_dict() for ev in it.trace]
            out(res)
        else:
            if args.trace:
                for ev in it.trace:
                    where = f"{ev.span['line']}:{ev.span['col']}"
                    if ev.event == "assign":
                        print(f"[{ev.step:>4}] {where:>6}  {ev.detail['var']} := {ev.detail['value']}")
                    elif ev.event == "cond":
                        print(f"[{ev.step:>4}] {where:>6}  умова {ev.detail['kind']}: "
                              f"{str(ev.detail['value']).lower()}")
                    elif ev.event == "skip":
                        print(f"[{ev.step:>4}] {where:>6}  skip")
            print("Кінцевий стан: " + (", ".join(f"{k} = {v}" for k, v in final.items())
                                       or "порожній"))
        return EXIT_OK

    if args.cmd == "tree":
        from . import visualization as V
        try:
            if as_json or args.format == "json":
                text = V.to_json(tree, source)
            elif args.format == "dot":
                text = V.to_dot(tree, source)
            elif args.format == "svg":
                text = V.to_svg(tree, source)
            else:
                text = V.to_text(tree, source)
        except RuntimeError as e:
            return fail(EXIT_USAGE, str(e))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Записано у {args.output}")
        else:
            print(text)
        return EXIT_OK

    from .semantics import build_term, evaluate, explain
    from .semantics.terms import to_dict as term_dict
    term = build_term(program)

    if args.cmd == "term":
        if as_json:
            res = {"ok": True, "term": term.render(args.format), "tree": term_dict(term)}
            if args.explain:
                res["steps"] = [s.to_dict() for s in explain(program, source, args.format)]
            out(res)
        elif args.explain:
            steps = explain(program, source, args.format)
            print("\n\n".join(s.text() for s in steps))
            print("\nТерм програми:\nsem_P(P) = " + term.render(args.format))
        else:
            print(term.render(args.format))
        return EXIT_OK

    if args.cmd == "eval":
        res = evaluate(term, st, "ascii" if args.ascii else "text", args.max_iterations)
        if as_json:
            out({"ok": res.state is not None, **res.to_dict()})
        else:
            print(res.text())
        return EXIT_OK if res.state is not None else EXIT_UNDEFINED

    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
