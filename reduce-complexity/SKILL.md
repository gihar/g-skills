---
name: reduce-complexity
description: >-
  Use when asked to reduce, lower, cut, or refactor cyclomatic complexity of a
  codebase — e.g. "reduce cyclomatic complexity", "refactor the D/E/F functions",
  "снизь сложность", "what's the complexity of this project". Works for Python
  (radon) and JavaScript/TypeScript (ESLint `complexity`). Encodes a safe workflow:
  measure → lock behaviour with tests → extract helpers → verify with zero new
  lint/type regressions.
version: 1.0.0
---

# Reduce Cyclomatic Complexity

Behaviour-preserving complexity reduction. The golden rule: **never change
behaviour** — lock it with tests first (or rely on existing ones), extract
helpers, then prove the grade dropped with **zero new lint/type regressions**.

Grade scale (radon CC; apply the same buckets to ESLint complexity counts):
`A`=1–5, `B`=6–10, `C`=11–20, `D`=21–30, `E`=31–40, `F`=41+. Target: pull every
function out of its grade — F/E/D → ideally A/B, at minimum below the next threshold.

> Adapt the example commands below to the project's toolchain (package manager,
> source dirs, test runner). Detect them first: look for `pyproject.toml`/`poetry.lock`/
> `requirements.txt` (Python) and `package.json` (JS/TS), and honour any repo hooks,
> pre-commit gates, or CI conventions.

## 1. Measure first

**Python — [radon](https://radon.readthedocs.io/):**
```bash
radon cc <src_dir> -a -s --total-average | tail -3   # average + total
radon cc <src_dir> -s -n D                           # D, E and F blocks (worst first)
radon cc <src_dir> -s -n F                           # F only / re-check after
```
If radon is missing: `pip install radon` (or `poetry run pip install radon` /
`uv pip install radon`). `radon cc <file> -s` prints the file path above each
block → that gives you `file:line`.

**JS/TS — ESLint's built-in `complexity` rule** (no extra dep). Drive it with
threshold 1 and parse the JSON:
```bash
npx eslint "<src_glob>" --rule '{"complexity":["warn",1]}' --format json 2>/dev/null > /tmp/cc.json
node -e 'const r=JSON.parse(require("fs").readFileSync("/tmp/cc.json","utf8"));let v=[];for(const f of r)for(const m of f.messages){const x=/complexity of (\d+)/.exec(m.message);if(x)v.push({c:+x[1],f:f.filePath+":"+m.line})}v.sort((a,b)=>b.c-a.c);for(const e of v.slice(0,15))console.log(String(e.c).padStart(3),e.f)'
```
F-grade is CC ≥ 41.

## 2. Scope and branch

- Pick targets by grade (do F, then E, then D). For a batch, list the worst
  offenders as `file:line (CC)` and confirm scope with the user when it includes
  **one-off scripts / generated code / vendored files** — those are often
  untested and lower value; default to skipping unless asked.
- Use a dedicated branch, e.g. `refactor/reduce-<grade>-complexity`. One branch
  per grade batch.

## 3. Per-function discipline (the core loop)

For **each** target function:

1. **Read it fully**; find its callers (`grep -rn "<name>" <src_dir>`) and any
   existing tests.
2. **Establish a green baseline** — run the existing tests; they must pass before
   you touch anything.
3. **If the function is UNTESTED → write a characterization test FIRST** that
   passes on the *current* code, locking observable behaviour. Then refactor, then
   re-run — it must still pass. This is the safety net; do not skip it.
4. **Extract helpers — move code, don't rewrite logic.** Behaviour stays identical.
5. **Verify** (section 4). Only then move on.

### Extraction patterns

**General / backend:**
- **Shared builder for duplicated logic** — when two functions build an identical
  dict/result (e.g. a `list_X` and a `get_X`), extract one helper used by both.
  Dedup + the branch-heavy block leaves both callers.
- **Filter / query builders** — `build_X_filters(...) -> list`,
  `apply_X(query, ...) -> query`.
- **Declarative maps** to collapse long `if param is not None: out[k]=param` chains
  into a loop over a field list; keep special cases separate.
- **Extract loop bodies / distinct branches** of long procedures into named helpers.
- **Raw-SQL/string condition builders** — `build_conditions(...) -> (clauses, params)`
  + a `row_to_dict(row)` for result mapping.

**Frontend (React/JSX):**
- Extract **sub-components** for repeated/duplicated JSX (table headers, rows,
  radio groups, pagination). Move JSX **verbatim** — identical classNames,
  handlers, conditions, DOM — and thread values/handlers as props.
- Extract **pure module-level helpers** for big boolean expressions and for
  `useMemo` bodies (keep the same dependency arrays).
- **Keep all hooks at the top of the component in their original order** — never
  move a hook into a conditional (rules-of-hooks).

## 4. Verify — tests + grade drop + zero new regressions

**No new regressions** is mandatory. Many codebases carry pre-existing lint/type
debt — measure **deltas vs the base commit**, don't chase a globally clean run.

```bash
# 1) tests for the touched files must pass (use the project's runner)
<test runner> <touched test files>
# 2) the grade dropped
radon cc <file> -s | grep -E "<fn>|<new helpers>"      # or re-run the ESLint CC scan
# 3) lint delta vs HEAD (parity or better) — compare counts
git show HEAD:<path> > /tmp/before && <linter> /tmp/before | grep -c .   # before
<linter> <path> | grep -c .                                              # after (<= before)
# 4) type-check delta (per file, after <= before)
<type checker> <path>
```
- Python: `pytest`, `ruff check`, `mypy <file>` (count in-file errors before/after).
- JS/TS: project test runner, `eslint <file>`, `tsc --noEmit` (whole project must
  stay at its baseline). **If a project has no unit tests** (common on frontends),
  the safety net is type-check + lint + **reading each diff** to confirm every
  extraction is a verbatim move (classNames/conditions/handlers unchanged, props
  wired correctly, hook order intact).

Match the file's existing typing/lint conventions; if a new annotation would *add*
an error, prefer the convention already in the file.

## 5. Batch independent files with parallel subagents

When refactoring several functions across **different files**, dispatch one
subagent per file (independent → run concurrently). Give each: the exact
`file:line` + current CC, the extraction plan, the "move verbatim / characterize-
first if untested" mandate, the verification commands, and "do NOT commit". Then
**independently re-verify the aggregate yourself** — re-scan CC (no D/E/F left, no
new high-grade helper), run all touched tests together, check lint/type/CC deltas,
and **review the diffs** — before committing. Do not trust subagent self-reports
for the merge decision.

## 6. Commit conventions

- `refactor: cut cyclomatic complexity of <the N grade-X functions>`, with a body
  listing each function `D(29) -> A(5)` and the helpers extracted, plus "Behaviour
  preserved; locked with characterization tests; no new lint/type regressions."
- Stage **only** the refactored source + new test files; leave unrelated changes alone.

## Notes & gotchas

- `radon` / ESLint `complexity` count every `if`/`for`/`while`/`and`/`or`/ternary/
  comprehension. A flat data-mapping helper can still be grade C — that's fine; the
  goal is pulling the *control-flow-heavy* function out of its grade, not gold-plating.
- Don't over-extract dispatch loops — a top-level loop at C(11–12) reads better than
  one scattered into B. Stop once it's safely out of the target grade.
- Shell working directory may persist between commands but shell state usually does
  not; prefer absolute paths or `cd` once per block.
