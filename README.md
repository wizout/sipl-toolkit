# SIPL Toolkit

[![tests](https://github.com/wizout/sipl-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/wizout/sipl-toolkit/actions/workflows/ci.yml)

Інструменти для мови SIPL з курсу «Теорія програмування»: граматика, парсер, інтерпретатор,
дерево синтаксичного виводу, побудова семантичного терму і його обчислення на стані.
Фактично це практичні роботи 1 і 2, які роблять програма, а не ручка.

Автор: Котілєвський Григорій, ТК-31.

## Обрані завдання (трек «Формальна семантика», 10 балів)

| ID | Завдання | Бали | Де в коді |
|----|----------|-----:|-----------|
| CORE-01 | Формальна граматика (Lark/EBNF), ≥10 правильних і ≥10 неправильних прикладів | 0.5 | `grammar/sipl.lark`, `examples/ok`, `examples/bad`, `tests/test_grammar.py` |
| CORE-02 | Парсер і власне AST з позиціями (SourceSpan), зрозумілі синтаксичні помилки | 1.5 | `src/sipl/lexer.py`, `parser.py`, `ast.py`, `errors.py` |
| CORE-03 | Інтерпретатор: присвоєння, `;`, if, while, begin/end, skip; ліміт кроків; покриття тестами ≥80% | 2.0 | `src/sipl/interpreter.py` |
| VIS-01 | Дерево синтаксичного виводу: text, JSON, DOT, SVG; вузли прив'язані до тексту | 1.5 | `src/sipl/visualization/tree.py` |
| SEM-01 | Семантичний терм у нотації курсу, рекурсивно з AST, golden-тести | 2.0 | `src/sipl/semantics/terms.py`, `build.py`, `tests/golden` |
| SEM-02 | Обчислення терму на стані: кінцевий стан або ⊥ і траса застосованих правил | 2.0 | `src/sipl/semantics/evaluate.py` |
| REL-02 | GitHub Release + SemVer + CHANGELOG | 0.5 | `CHANGELOG.md`, `.github/workflows/release.yml` |
| | **Разом** | **10.0** | |

## Встановлення

Потрібен Python 3.10 або новіший. Залежностей у самого пакета немає.

```bash
git clone https://github.com/wizout/sipl-toolkit.git
cd sipl-toolkit
python -m pip install -e ".[dev]"     # на Windows: py -m pip install -e ".[dev]"
```

Після цього з'являється команда `sipl` (або `python -m sipl`).
Для `tree --format svg` треба ще [Graphviz](https://graphviz.org/download/) (команда `dot`),
решта працює без нього.

## Як користуватись

Приклад програми `examples/ok/power.sipl` (R = X^Y):

```
begin
    R := 1;
    while Y > 0 do
    begin
        R := R * X;
        Y := Y - 1
    end
end
```

### Перевірка синтаксису і помилки

```text
$ sipl check examples/ok/power.sipl
Синтаксис правильний.

$ sipl check examples/bad/missing_semicolon.sipl
Помилка: рядок 3, колонка 5: між операторами потрібна ';' перед 'Y'
      Y := 2
      ^
```

### Виконання

```text
$ sipl run examples/ok/prime.sipl --set N=7
Кінцевий стан: N = 7, R = 1, D = 7

$ sipl run examples/ok/factorial.sipl -s N=3 --trace     # покроково
```

### Дерево синтаксичного виводу (практична 1)

```text
$ sipl tree examples/ok/power.sipl
<програма>   [P]   2:1
├── begin   (1)   2:1
├── <оператор>   [S_Seq]   3:5
│   ├── <оператор>   [S_As]   3:5
│   │   ├── <змінна>   3:5
│   │   │   └── R   (2)   3:5
...
Листки зліва направо: 1 begin 2 R 3 := 4 1 5 ; 6 while ...
```

У квадратних дужках правило БНФ, у круглих номер листка, далі рядок:колонка.
Інші формати: `-f json` (кожен вузол має `span` і `text` з фрагментом коду),
`-f dot`, `-f svg -o tree.svg` (при наведенні на вузол видно його фрагмент коду).

### Семантичний терм (практична 2)

```text
$ sipl term examples/ok/power.sipl --explain
NS_Prog, NS_Stm_Seq, NS_Stm_As, NS_A_Num:
sem_P(P) = AS^R(1̅) · sem_S(while Y > 0 do ...)

NS_Stm_Wh, NS_B_gr, NS_A_Var, NS_A_Num, NS_Stm_BE, NS_Stm_Seq, NS_Stm_As, NS_A_Mult, NS_A_Sub:
sem_S(while Y > 0 do ...) = WH(S^2(gr, Y⇒, 0̅), AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1̅)))

Терм програми:
sem_P(P) = AS^R(1̅) · WH(S^2(gr, Y⇒, 0̅), AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1̅)))
```

Формати: `-f text` (риска над константою), `-f ascii` (`~1`, `=>`), `-f latex`, `--json`.

### Обчислення терму на стані (тестування з практичної 2)

```text
$ sipl eval examples/ok/power.sipl -s X=2 -s Y=1
st = [X ↦ 2, Y ↦ 1]
AF_SEQ: (AS^R(1̅) · WH(...))(st) = WH(...)(AS^R(1̅)(st))
AF_AS: AS^R(1̅)(st) = st∇[R ↦ 1̅(st)] = st∇[R ↦ 1] = [X ↦ 2, Y ↦ 1, R ↦ 1] = st₁
AF_S, AF_DNM: S^2(gr, Y⇒, 0̅)(st₁) = gr(Y⇒(st₁), 0̅(st₁)) = gr(1, 0) = true

Ітерація 1
AF_WH: WH(...)(st₁) = WH(...)((AS^R(...) · AS^Y(...))(st₁))
...
AF_WH: WH(...)(st₃) = st₃, умова false - цикл завершено
Результат: st₃ = [X ↦ 2, Y ↦ 0, R ↦ 2]
```

Якщо змінної немає в стані, ділимо на 0 або цикл не закінчується за `--max-iterations`,
результат «невизначено (⊥)» з поясненням, код завершення 3.

`sipl rules` друкує всі правила NS_* і AF_*.

### Коди завершення

| код | значення |
|----:|----------|
| 0 | все добре |
| 1 | синтаксична помилка |
| 2 | неправильні аргументи (наприклад `--set N=abc`) |
| 3 | програма невизначена на цьому стані |
| 4 | файл не знайдено |

З `--json` кожна команда друкує JSON: `{"ok": true, ...}` або
`{"ok": false, "error": {"kind", "message", "span"}}`.

## Мова

Граматика: `grammar/sipl.lark`. Там правила бази і розширення позначені коментарями.

### SIPL (база з практикуму)

```
<програма> ::= begin <оператор> end
<оператор> ::= x := a | S1 ; S2 | if b then S1 else S2 | while b do S | begin S end | skip
<вираз>    ::= n | x | a1 + a2 | a1 - a2 | a1 * a2 | ( a )
<умова>    ::= true | false | a1 < a2 | a1 = a2 | a1 > a2 | not b | b1 and b2 | b1 or b2 | ( b )
```

Логічні операції пишуться словами: `not`, `and`, `or` замість ¬, ∧, ∨.

### SIPL+ (розширення цього проєкту)

Додано те, що потрібно у варіантах задач з практичних (наприклад, перевірка простоти через `mod`):

| що додано | правило | функція в термі | правило побудови терму |
|---|---|---|---|
| ціле ділення | `a1 div a2` | `div` | NS_A_Div |
| остача | `a1 mod a2` | `mod` | NS_A_Mod |
| менше або дорівнює | `a1 <= a2` | `leq` | NS_B_leq |
| більше або дорівнює | `a1 >= a2` | `geq` | NS_B_geq |
| не дорівнює | `a1 <> a2` | `neq` | NS_B_neq |
| коментарі | `// до кінця рядка` | | |

`div` і `mod` мають той самий пріоритет, що й `*`. Ділення на 0 дає невизначеність (⊥).
Програма, написана тільки базою, розбирається і рахується так само, як без розширень,
тому розширення нічого не ламають.

### Пріоритети

Як у практичній 1: `;` слабше за `if` і `while` (тіло циклу з кількох операторів
береться в `begin ... end`), `S1; S2; S3` = `(S1; S2); S3`, `* div mod` сильніше за `+ -`,
у умовах `not` сильніше за `and`, а `and` сильніше за `or`.
Програма завжди `begin ... end`, у `if` гілка `else` обов'язкова (можна `else skip`).

Функції в термах: `add sub mult` (база) і `div mod` (розширення) для виразів,
`ls eq gr` (база) і `leq geq neq` (розширення) для порівнянь, `and or neg` для логіки.

## Структура

```
grammar/sipl.lark          формальна граматика
src/sipl/
  lexer.py                 текст -> токени з позиціями
  parser.py                токени -> дерево виводу -> AST
  ast.py                   вузли AST
  errors.py                SourceSpan і помилки
  interpreter.py           виконання AST
  visualization/tree.py    дерево виводу: text/json/dot/svg
  semantics/terms.py       терми і їх запис
  semantics/build.py       AST -> терм (правила NS_*)
  semantics/evaluate.py    терм + стан -> результат і траса (правила AF_*)
  cli.py                   команда sipl
examples/ok, examples/bad  правильні та неправильні програми
tests/                     pytest, golden-файли термів
docs/architecture.md       як дані проходять через шари
```

## Тести

```bash
python -m pytest --cov=sipl
```

Тести перевіряють, зокрема, що граматика в `sipl.lark` і парсер дають однакову структуру
на всіх прикладах, що терм програми з практичної 2 будується символ у символ, і що
обчислення терму дає той самий стан, що й інтерпретатор.

## Обмеження

- Значення змінних тільки цілі числа, `div` і `mod` рахуються як у Python (`//`, `%`).
- Нескінченний цикл не можна розпізнати в загальному випадку, тому є ліміт кроків
  (`--max-steps` для `run`, `--max-iterations` для `eval`), після якого результат
  вважається невизначеним.
- Терм обчислюється на конкретному стані, це тестування, а не доведення коректності.

## Реліз

Версії за SemVer, зміни в `CHANGELOG.md`. Щоб випустити реліз:

```bash
git tag v0.5.0
git push origin v0.5.0
```

GitHub Actions (`release.yml`) прожене тести, збере wheel і sdist і створить
GitHub Release з нотатками з CHANGELOG.

## Ліцензія

MIT
