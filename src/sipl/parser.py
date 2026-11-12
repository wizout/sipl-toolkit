"""Парсер SIPL методом рекурсивного спуску.

Робота йде у два кроки:
  1. текст -> дерево синтаксичного виводу (ParseNode), як у практичній 1:
     вузли - метазмінні <оператор>, <вираз>, ..., листки - термінали;
  2. дерево виводу -> AST (to_ast): викидаємо дужки, ключові слова і ';'.

Пріоритети такі ж, як у практичній 1: ';' зв'язує слабше за if і while,
послідовне виконання лівоасоціативне: S1; S2; S3 = (S1; S2); S3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ast as A
from .errors import SiplSyntaxError, SourceSpan
from .lexer import Token, tokenize

# правила граматики: назва -> текст правила у БНФ (для пояснень і візуалізації)
RULES = {
    "P":       "<програма> ::= begin <оператор> end",
    "S_As":    "<оператор> ::= <змінна> := <вираз>",
    "S_Seq":   "<оператор> ::= <оператор> ; <оператор>",
    "S_If":    "<оператор> ::= if <умова> then <оператор> else <оператор>",
    "S_While": "<оператор> ::= while <умова> do <оператор>",
    "S_Block": "<оператор> ::= begin <оператор> end",
    "S_Skip":  "<оператор> ::= skip",
    "A_Num":   "<вираз> ::= <число>",
    "A_Var":   "<вираз> ::= <змінна>",
    "A_Add":   "<вираз> ::= <вираз> + <вираз>",
    "A_Sub":   "<вираз> ::= <вираз> - <вираз>",
    "A_Mult":  "<вираз> ::= <вираз> * <вираз>",
    "A_Div":   "<вираз> ::= <вираз> div <вираз>",
    "A_Mod":   "<вираз> ::= <вираз> mod <вираз>",
    "A_Par":   "<вираз> ::= ( <вираз> )",
    "B_True":  "<умова> ::= true",
    "B_False": "<умова> ::= false",
    "B_Less":  "<умова> ::= <вираз> < <вираз>",
    "B_Leq":   "<умова> ::= <вираз> <= <вираз>",
    "B_Eq":    "<умова> ::= <вираз> = <вираз>",
    "B_Neq":   "<умова> ::= <вираз> <> <вираз>",
    "B_Gr":    "<умова> ::= <вираз> > <вираз>",
    "B_Geq":   "<умова> ::= <вираз> >= <вираз>",
    "B_Not":   "<умова> ::= not <умова>",
    "B_And":   "<умова> ::= <умова> and <умова>",
    "B_Or":    "<умова> ::= <умова> or <умова>",
    "B_Par":   "<умова> ::= ( <умова> )",
}

ARITH_RULE = {"+": "A_Add", "-": "A_Sub", "*": "A_Mult", "div": "A_Div", "mod": "A_Mod"}
CMP_RULE = {"<": "B_Less", "<=": "B_Leq", "=": "B_Eq", "<>": "B_Neq", ">": "B_Gr", ">=": "B_Geq"}
STMT_START = {"if", "while", "begin", "skip"}


@dataclass
class ParseNode:
    """Вузол дерева виводу. Листок має token, внутрішній вузол - rule і children."""
    symbol: str
    span: SourceSpan
    rule: str | None = None
    children: list["ParseNode"] = field(default_factory=list)
    token: Token | None = None

    @property
    def is_leaf(self) -> bool:
        return self.token is not None

    def leaves(self) -> list["ParseNode"]:
        if self.is_leaf:
            return [self]
        out = []
        for c in self.children:
            out += c.leaves()
        return out


def leaf(tok: Token) -> ParseNode:
    return ParseNode(tok.value, tok.span, token=tok)


def node(symbol: str, rule: str, *children: ParseNode) -> ParseNode:
    return ParseNode(symbol, children[0].span.join(children[-1].span), rule, list(children))


class Parser:
    def __init__(self, source: str):
        self.source = source
        self.tokens = tokenize(source)
        self.pos = 0

    # допоміжне

    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def at(self, *values: str) -> bool:
        t = self.cur
        return t.kind in ("kw", "op") and t.value in values

    def take(self) -> Token:
        t = self.cur
        self.pos += 1
        return t

    def expect(self, value: str, hint: str = "") -> Token:
        if self.at(value):
            return self.take()
        msg = f"очікувалось '{value}', а знайдено {self.cur}"
        raise SiplSyntaxError(msg + (f" ({hint})" if hint else ""), self.cur.span)

    # програма і оператори

    def program(self) -> ParseNode:
        if not self.at("begin"):
            raise SiplSyntaxError(f"програма має починатись з 'begin', а знайдено {self.cur}",
                                  self.cur.span)
        b = leaf(self.take())
        body = self.statements()
        e = leaf(self.expect("end", "кожному begin потрібен свій end"))
        if self.cur.kind != "eof":
            raise SiplSyntaxError(f"зайвий текст після кінця програми: {self.cur}", self.cur.span)
        return node("<програма>", "P", b, body, e)

    def statements(self) -> ParseNode:
        # S1 ; S2 ; S3 збираю зліва направо: ((S1; S2); S3)
        left = self.statement()
        while True:
            if self.at(";"):
                semi = leaf(self.take())
                if self.at("end") or self.cur.kind == "eof":
                    raise SiplSyntaxError("після ';' очікувався оператор (зайва ';' перед end?)",
                                          semi.span)
                right = self.statement()
                left = node("<оператор>", "S_Seq", left, semi, right)
            elif self.cur.kind == "id" or self.at(*STMT_START):
                raise SiplSyntaxError(f"між операторами потрібна ';' перед {self.cur}",
                                      self.cur.span)
            else:
                return left

    def statement(self) -> ParseNode:
        t = self.cur
        if t.kind == "id":
            var = node("<змінна>", None, leaf(self.take()))
            if self.at("="):
                raise SiplSyntaxError("присвоєння пишеться ':=', а не '='", self.cur.span)
            op = leaf(self.expect(":="))
            return node("<оператор>", "S_As", var, op, self.aexpr())
        if self.at("if"):
            kw = leaf(self.take())
            cond = self.bexpr()
            th = leaf(self.expect("then"))
            s1 = self.statement()
            el = leaf(self.expect("else", "в SIPL у if обов'язкова гілка else, можна else skip"))
            s2 = self.statement()
            return node("<оператор>", "S_If", kw, cond, th, s1, el, s2)
        if self.at("while"):
            kw = leaf(self.take())
            cond = self.bexpr()
            do = leaf(self.expect("do"))
            return node("<оператор>", "S_While", kw, cond, do, self.statement())
        if self.at("begin"):
            b = leaf(self.take())
            body = self.statements()
            e = leaf(self.expect("end", "кожному begin потрібен свій end"))
            return node("<оператор>", "S_Block", b, body, e)
        if self.at("skip"):
            return node("<оператор>", "S_Skip", leaf(self.take()))
        raise SiplSyntaxError(f"очікувався оператор, а знайдено {t}", t.span)

    # арифметичні вирази

    def aexpr(self) -> ParseNode:
        left = self.term()
        while self.at("+", "-"):
            op = self.take()
            left = node("<вираз>", ARITH_RULE[op.value], left, leaf(op), self.term())
        return left

    def term(self) -> ParseNode:
        left = self.factor()
        while self.at("*", "div", "mod"):
            op = self.take()
            left = node("<вираз>", ARITH_RULE[op.value], left, leaf(op), self.factor())
        return left

    def factor(self) -> ParseNode:
        t = self.cur
        if t.kind == "num":
            return node("<вираз>", "A_Num", node("<число>", None, leaf(self.take())))
        if t.kind == "id":
            return node("<вираз>", "A_Var", node("<змінна>", None, leaf(self.take())))
        if self.at("("):
            lp = leaf(self.take())
            inner = self.aexpr()
            rp = leaf(self.expect(")"))
            return node("<вираз>", "A_Par", lp, inner, rp)
        raise SiplSyntaxError(f"очікувався вираз (число, змінна або дужка), а знайдено {t}",
                              t.span)

    # умови

    def bexpr(self) -> ParseNode:
        left = self.bterm()
        while self.at("or"):
            op = self.take()
            left = node("<умова>", "B_Or", left, leaf(op), self.bterm())
        return left

    def bterm(self) -> ParseNode:
        left = self.bfactor()
        while self.at("and"):
            op = self.take()
            left = node("<умова>", "B_And", left, leaf(op), self.bfactor())
        return left

    def bfactor(self) -> ParseNode:
        if self.at("not"):
            kw = leaf(self.take())
            return node("<умова>", "B_Not", kw, self.bfactor())
        if self.at("true"):
            return node("<умова>", "B_True", leaf(self.take()))
        if self.at("false"):
            return node("<умова>", "B_False", leaf(self.take()))
        if self.at("("):
            # дужка може відкривати і вираз "(x + 1) > 2", і умову "(x > 1) and ..."
            # спершу пробую як порівняння, якщо не вийшло - як умову в дужках
            save = self.pos
            try:
                return self.comparison()
            except SiplSyntaxError as e1:
                err1, self.pos = e1, save
            try:
                lp = leaf(self.take())
                inner = self.bexpr()
                rp = leaf(self.expect(")"))
                return node("<умова>", "B_Par", lp, inner, rp)
            except SiplSyntaxError as e2:
                # показую ту помилку, що зайшла далі по тексту
                raise e2 if e2.span.offset >= err1.span.offset else err1
        return self.comparison()

    def comparison(self) -> ParseNode:
        left = self.aexpr()
        if not self.at(*CMP_RULE):
            raise SiplSyntaxError(f"очікувалось порівняння (<, <=, =, <>, >, >=), а знайдено {self.cur}",
                                  self.cur.span)
        op = self.take()
        return node("<умова>", CMP_RULE[op.value], left, leaf(op), self.aexpr())


# дерево виводу -> AST

def to_ast(p: ParseNode) -> A.Node:
    r, ch, sp = p.rule, p.children, p.span
    if r == "P":
        return A.Program(sp, to_ast(ch[1]))
    if r == "S_As":
        return A.Assign(sp, ch[0].children[0].token.value, to_ast(ch[2]))
    if r == "S_Seq":
        return A.Seq(sp, to_ast(ch[0]), to_ast(ch[2]))
    if r == "S_If":
        return A.If(sp, to_ast(ch[1]), to_ast(ch[3]), to_ast(ch[5]))
    if r == "S_While":
        return A.While(sp, to_ast(ch[1]), to_ast(ch[3]))
    if r == "S_Block":
        return A.Block(sp, to_ast(ch[1]))
    if r == "S_Skip":
        return A.Skip(sp)
    if r == "A_Num":
        return A.Num(sp, int(ch[0].children[0].token.value))
    if r == "A_Var":
        return A.Var(sp, ch[0].children[0].token.value)
    if r in ("A_Par", "B_Par"):
        return to_ast(ch[1])            # дужки в AST не потрібні
    if r in ("A_Add", "A_Sub", "A_Mult", "A_Div", "A_Mod"):
        return A.BinOp(sp, ch[1].token.value, to_ast(ch[0]), to_ast(ch[2]))
    if r in CMP_RULE.values():
        return A.Compare(sp, ch[1].token.value, to_ast(ch[0]), to_ast(ch[2]))
    if r in ("B_True", "B_False"):
        return A.BoolConst(sp, r == "B_True")
    if r == "B_Not":
        return A.Not(sp, to_ast(ch[1]))
    if r in ("B_And", "B_Or"):
        return A.BoolOp(sp, ch[1].token.value, to_ast(ch[0]), to_ast(ch[2]))
    raise ValueError(f"невідоме правило {r}")


def parse_tree(source: str) -> ParseNode:
    return Parser(source).program()


def parse(source: str) -> A.Program:
    return to_ast(parse_tree(source))
