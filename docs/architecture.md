# Архітектура

```
текст -> lexer -> parser -> дерево виводу -> AST -> interpreter -> стан
                                 |             +-> semantics.build -> терм -> semantics.evaluate -> стан / ⊥
                                 +-> visualization
```

- lexer.py: текст в токени з позиціями
- parser.py: рекурсивний спуск, будує дерево виводу, потім `to_ast` робить AST
- interpreter.py: виконує AST, стан це dict, є ліміт кроків
- semantics/build.py: AST в терм за правилами NS
- semantics/evaluate.py: рахує терм на стані за правилами AF і пише кроки
- visualization/tree.py: дерево виводу в text, json, dot, svg
- cli.py: команди check, parse, run, tree, term, eval, rules
