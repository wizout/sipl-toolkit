# sipl-toolkit

[![tests](https://github.com/wizout/sipl-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/wizout/sipl-toolkit/actions/workflows/ci.yml)

Проєкт з теорії програмування, Котілєвський Григорій, ТК-31.

Парсер і інтерпретатор для SIPL, плюс дерево виводу (практична 1) і семантичні терми
(практична 2), які раніше рахували руками.

Обрав трек "Формальна семантика", разом 10 балів:

- CORE-01 граматика (0.5)
- CORE-02 парсер і AST (1.5)
- CORE-03 інтерпретатор (2)
- VIS-01 дерево виводу (1.5)
- SEM-01 побудова терму (2)
- SEM-02 обчислення терму на стані (2)
- REL-02 реліз (0.5)

## Як запустити

Треба Python 3.10 або новіше.

```
git clone https://github.com/wizout/sipl-toolkit.git
cd sipl-toolkit
py -m pip install -e ".[dev]"
```

Приклади команд:

```
py -m sipl check examples/ok/power.sipl
py -m sipl run examples/ok/power.sipl -s X=2 -s Y=3
py -m sipl tree examples/ok/power.sipl
py -m sipl term examples/ok/power.sipl --explain
py -m sipl eval examples/ok/power.sipl -s X=2 -s Y=1
py -m sipl rules
```

`-s` задає початковий стан. У `tree` є ще `-f json`, `-f dot` і `-f svg -o tree.svg`
(для svg треба поставити Graphviz). У всіх команд є `--json`.

Тести:

```
py -m pytest --cov=sipl
```

## Про мову

Граматика лежить в `grammar/sipl.lark`, вона така сама як БНФ з практикуму. Я ще додав
`div`, `mod`, `<=`, `>=`, `<>` і коментарі `//`, бо вони трапляються у варіантах. У граматиці
вони підписані `[SIPL+]`, програми без них працюють як раніше.

`else` писати обов'язково, якщо нічого не треба робити то `else skip`. Тіло циклу з кількох
операторів береться в `begin ... end`.

## Що не вміє

Тільки цілі числа. Чи закінчиться цикл наперед не визначити, тому стоїть ліміт ітерацій і
після нього результат вважається невизначеним. `eval` просто рахує на конкретному стані, це
не доведення правильності.

Як влаштований код розписав в `docs/architecture.md`.

Реліз збирається сам, коли пушу тег (`.github/workflows/release.yml`).
