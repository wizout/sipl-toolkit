from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpan:
    line: int
    col: int
    end_line: int
    end_col: int
    offset: int
    end_offset: int

    def join(self, other: "SourceSpan") -> "SourceSpan":
        return SourceSpan(
            self.line, self.col, other.end_line, other.end_col, self.offset, other.end_offset
        )

    def text(self, source: str) -> str:
        return source[self.offset : self.end_offset]

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "col": self.col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }

    def __str__(self) -> str:
        return f"{self.line}:{self.col}"


class SiplError(Exception):
    kind = "error"

    def __init__(self, message: str, span: SourceSpan | None = None):
        super().__init__(message)
        self.message = message
        self.span = span

    def __str__(self) -> str:
        if self.span is None:
            return self.message
        return f"рядок {self.span.line}, колонка {self.span.col}: {self.message}"

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "message": self.message,
            "span": self.span.to_dict() if self.span else None,
        }


class SiplSyntaxError(SiplError):
    kind = "syntax"


class SiplRuntimeError(SiplError):
    kind = "runtime"
