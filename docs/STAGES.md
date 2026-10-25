# Stage-by-stage presenter guide

Before each stage:

```bash
git checkout <branch>
uv run python -m factory reset && uv run python -m factory setup
```

---

## Stage 1: `stage-1-naive`

**Adds:** intake, worktree, one agent run, draft PR.

**Run:** `uv run python -m factory run-all`

**Expected:** all three issues produce a PR.

- `001` is correct.
- `002` has an off-by-one bug: 10 units get no bulk discount.
- `003` changed `tax()` and `total()` to return strings, and edited an existing test so it still passes.

**Point to make:** the agent reported success every time. Nothing in this pipeline can tell the
difference between the good PR and the bad ones, so a human reviewer must catch all of it.
Show the diff of `003` on its branch:
`git -C .demo/target diff main factory/003-tax-rounding`

---

## Stage 2: `stage-2-gates`

**Adds:** `gates.py`: tests, lint, protected paths and human-written acceptance tests.

**Diff:** `git diff stage-1-naive stage-2-gates -- factory/`

**Expected:** `001` opens a PR; `002` and `003` are escalated.

- `002` fails the acceptance test for exactly 10 units.
- `003` fails twice over: acceptance tests, and **protected paths** (it modified `tests/test_cart.py`).

**Point to make:** pass or fail is decided by exit codes, not by asking the agent. The
protected-path check is about ten lines and stops the most common way agents "fix" failing
tests. But stopping at the first failure wastes the run.

---

## Stage 3: `stage-3-retry`

**Adds:** a retry loop that feeds the gate output back to the agent (max 3 attempts).

**Diff:** `git diff stage-2-gates stage-3-retry -- factory/ prompts/`

**Expected:** all three open a PR. `002` succeeds on attempt 2, `003` on attempt 2.

**Point to make:** this is the loop that makes agents useful: failures become the next prompt.
But look at `003`'s PR: it uses `round()`, which is banker's rounding. The issue asked for
half up. Every test passed because the acceptance tests had a gap.

```python
>>> round(0.125, 2)
0.12          # the issue requires 0.13
```

---

## Stage 4: `stage-4-review`

**Adds:** `review.py`: one LLM reviewer that must return JSON, validated in code, failing closed.

**Diff:** `git diff stage-3-retry stage-4-review -- factory/ prompts/`

**Run:** `uv run python -m factory run 003`

**Expected:** attempt 1 rejected by gates, attempt 2 **rejected in review** for banker's
rounding, attempt 3 accepted.

**Point to make:** review runs only after every deterministic check passes, so the LLM spends
its effort on what code cannot check: whether the change does what the issue meant. The
approval rule is still code: a reviewer that approves while listing a blocker is overruled.

---

## Stage 5: `stage-5-panel` (also `main`)

**Adds:** a panel of reviewers in parallel (correctness, security, conventions), SQLite state,
and a cost report.

**Diff:** `git diff stage-4-review stage-5-panel -- factory/ factory.toml`

**Run:**

```bash
uv run python -m factory run-all
uv run python -m factory accept 001
uv run python -m factory report
```

**Expected:** only the correctness reviewer rejects `003` attempt 2. The conventions reviewer
leaves a non-blocking note on `002`. The report includes the cost of failed attempts.

**Points to make:**

- This is where an agent team belongs: one stage, doing judgement in parallel. The team is a
  list in `factory.toml`; the rule for merging their verdicts is three lines of code.
- State lives in a database, not in an agent's context.
- Cost per *accepted* PR is the number that matters. It includes every failed attempt and is
  only known once a human merges.

---

## Optional live moments

- **Break a gate on purpose:** edit a replay patch, or set `max_attempts = 1` in
  `factory.toml`, and show the work being parked on a branch for a human.
- **Fail closed:** in `cli` review mode, point the review command at something that prints
  plain text. Every reviewer rejects.
- **Real agent:** switch `[agent] mode = "cli"` and run `001` live. Keep the replay as a backup.
