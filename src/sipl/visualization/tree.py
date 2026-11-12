"""Візуалізація дерева синтаксичного виводу (VIS-01): текст, JSON, DOT, SVG.

Кожен вузол знає свій span, тому в JSON є позиція і фрагмент коду, а в DOT/SVG
при наведенні на вузол видно, який шматок програми він виводить.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from ..parser import RULES, ParseNode

KEYWORDS = {"begin", "end", "if", "then", "else", "while", "do", "skip",
            "true", "false", "and", "or", "not", "div", "mod"}


def number_leaves(tree: ParseNode) -> dict[int, int]:
    """Нумерую листки зліва направо, як у практичній 1. Ключ - id() вузла."""
    return {id(l): i for i, l in enumerate(tree.leaves(), 1)}


def fragment(node: ParseNode, source: str) -> str:
    return " ".join(node.span.text(source).split())


# текст

def to_text(tree: ParseNode, source: str | None = None, show_rules: bool = True) -> str:
    nums = number_leaves(tree)
    lines = []

    def walk(n: ParseNode, prefix: str, last: bool, root: bool):
        branch = "" if root else ("└── " if last else "├── ")
        if n.is_leaf:
            label = f"{n.token.value}   ({nums[id(n)]})"
        else:
            label = n.symbol
            if show_rules and n.rule:
                label += f"   [{n.rule}]"
        label += f"   {n.span}"
        lines.append(prefix + branch + label)
        child_prefix = prefix + ("" if root else ("    " if last else "│   "))
        for i, c in enumerate(n.children):
            walk(c, child_prefix, i == len(n.children) - 1, False)

    walk(tree, "", True, True)
    leaves = tree.leaves()
    lines.append("")
    lines.append("Листки зліва направо: " +
                 " ".join(f"{i} {l.token.value}" for i, l in enumerate(leaves, 1)))
    lines.append(f"Всього листків: {len(leaves)}")
    return "\n".join(lines)


# JSON

def to_dict(tree: ParseNode, source: str) -> dict:
    nums = number_leaves(tree)

    def walk(n: ParseNode) -> dict:
        d = {"symbol": n.symbol, "span": n.span.to_dict(), "text": fragment(n, source)}
        if n.is_leaf:
            d["leaf"] = nums[id(n)]
            d["token"] = n.token.kind
        else:
            if n.rule:
                d["rule"] = n.rule
                d["bnf"] = RULES[n.rule]
            d["children"] = [walk(c) for c in n.children]
        return d

    return walk(tree)


def to_json(tree: ParseNode, source: str) -> str:
    return json.dumps(to_dict(tree, source), ensure_ascii=False, indent=2)


# DOT / SVG

def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def to_dot(tree: ParseNode, source: str) -> str:
    nums = number_leaves(tree)
    out = ["digraph ParseTree {",
           "  ordering=out; nodesep=0.15; ranksep=0.45;",
           '  node [shape=plaintext, fontname="DejaVu Sans", fontsize=13, margin=0, height=0.25];',
           "  edge [arrowsize=0.55, penwidth=0.9];"]
    counter = [0]

    def walk(n: ParseNode) -> str:
        counter[0] += 1
        me = f"n{counter[0]}"
        tip = esc(f"{n.span}: {fragment(n, source)}")
        if n.is_leaf:
            v = esc(n.token.value)
            txt = f"<B>{v}</B>" if n.token.value in KEYWORDS else v
            out.append(f'  {me} [label=<<FONT COLOR="red" POINT-SIZE="10">{nums[id(n)]} </FONT>'
                       f'{txt}>, tooltip="{tip}"];')
        else:
            rule = f" ({n.rule})" if n.rule else ""
            out.append(f'  {me} [label="{esc(n.symbol)}", tooltip="{tip}{esc(rule)}"];')
            for c in n.children:
                out.append(f"  {me} -> {walk(c)};")
        return me

    walk(tree)
    out.append("}")
    return "\n".join(out)


def to_svg(tree: ParseNode, source: str) -> str:
    """Потрібен Graphviz (команда dot). Якщо його немає - кидаю RuntimeError."""
    dot = shutil.which("dot")
    if not dot:
        raise RuntimeError("для SVG потрібен Graphviz (команда 'dot'); "
                           "можна взяти --format dot і відкрити у будь-якому переглядачі DOT")
    res = subprocess.run([dot, "-Tsvg"], input=to_dot(tree, source).encode("utf-8"),
                         capture_output=True, check=True)
    return res.stdout.decode("utf-8")
