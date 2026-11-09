"""Лексер: перетворює текст програми на список токенів з позиціями."""

from dataclasses import dataclass

from .errors import SiplSyntaxError, SourceSpan

KEYWORDS = {
    "begin", "end", "if", "then", "else", "while", "do", "skip",
    "true", "false", "and", "or", "not", "div", "mod",
}

# довші оператори стоять першими, щоб ":=" не розпалось на ":" і "="
OPERATORS = [":=", "<=", ">=", "<>", "+", "-", "*", "<", ">", "=", "(", ")", ";"]


@dataclass(frozen=True)
class Token:
    kind: str     # "num", "id", "kw", "op", "eof"
    value: str
    span: SourceSpan

    def __str__(self) -> str:
        return "кінець програми" if self.kind == "eof" else f"'{self.value}'"


def tokenize(source: str) -> list[Token]:
    tokens = []
    i, line, col = 0, 1, 1
    n = len(source)

    def span(start, s_line, s_col):
        return SourceSpan(s_line, s_col, line, col, start, i)

    while i < n:
        ch = source[i]
        # пробіли і переходи на новий рядок пропускаю, але рахую позицію
        if ch == "\n":
            i, line, col = i + 1, line + 1, 1
            continue
        if ch.isspace():
            i, col = i + 1, col + 1
            continue
        # коментар // до кінця рядка
        if source.startswith("//", i):
            while i < n and source[i] != "\n":
                i, col = i + 1, col + 1
            continue

        start, s_line, s_col = i, line, col
        if ch.isdigit():
            while i < n and source[i].isdigit():
                i, col = i + 1, col + 1
            if i < n and (source[i].isalpha() or source[i] == "_"):
                raise SiplSyntaxError("ім'я змінної не може починатись з цифри",
                                      SourceSpan(s_line, s_col, line, col + 1, start, i + 1))
            tokens.append(Token("num", source[start:i], span(start, s_line, s_col)))
            continue
        if ch.isalpha() or ch == "_":
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i, col = i + 1, col + 1
            word = source[start:i]
            kind = "kw" if word in KEYWORDS else "id"
            tokens.append(Token(kind, word, span(start, s_line, s_col)))
            continue
        for op in OPERATORS:
            if source.startswith(op, i):
                i, col = i + len(op), col + len(op)
                tokens.append(Token("op", op, span(start, s_line, s_col)))
                break
        else:
            raise SiplSyntaxError(f"невідомий символ '{ch}'",
                                  SourceSpan(line, col, line, col + 1, i, i + 1))

    tokens.append(Token("eof", "", SourceSpan(line, col, line, col, i, i)))
    return tokens
