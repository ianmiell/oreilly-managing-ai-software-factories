# Software Factory Starter

A minimal software factory for teaching: a **deterministic pipeline** that takes an
issue, runs a coding agent in an isolated git worktree, checks the result with code,
asks LLM reviewers for judgement, and hands a draft PR to a human.

The whole orchestrator is about 100 lines of plain Python. Every decision about what
happens next is an `if` statement you can read.

```
issue ─► worktree ─► agent ─► gates ─► review panel ─► draft PR ─► human merges
                       ▲         │           │
                       └─ retry with failure feedback (max 3) ─► escalate to a human
```

## Quick start (no API key needed)

Requires [uv](https://docs.astral.sh/uv/) and git. uv installs Python 3.11 if you
don't already have it.

```bash
uv venv --python 3.11                  # creates .venv
uv pip install -r requirements.txt
uv run python -m factory setup         # creates a demo repo in .demo/target
uv run python -m factory run 003       # watch one issue go through every stage
uv run python -m factory run-all       # or run all three demo issues
uv run python -m factory report        # spend, attempts and cost per accepted PR
uv run python -m factory reset         # start again
```

By default the agent and reviewers run in **replay mode**: they apply recorded patches
and verdicts, so the demo is identical every time, works offline and costs nothing.
The gates, retries, review merging and state are all real.

## Following the course stage by stage

Each branch adds one idea. Diff any two to see exactly what changed.

| Branch | Adds | What you see |
|---|---|---|
| `stage-1-naive` | intake, worktree, agent, PR | Buggy work goes straight to a PR |
| `stage-2-gates` | tests, lint, protected paths, acceptance tests | Bad work is caught, but the run just stops |
| `stage-3-retry` | failure output fed back to the agent | Most issues now succeed, one ships a subtle bug |
| `stage-4-review` | one schema-validated LLM reviewer | Review catches what the tests missed |
| `stage-5-panel` (= `main`) | parallel reviewer panel, SQLite state, cost report | The agent team as one stage, plus economics |

```bash
git checkout stage-2-gates
uv run python -m factory reset && uv run python -m factory setup
uv run python -m factory run-all
git diff stage-1-naive stage-2-gates -- factory/
```

See [docs/STAGES.md](docs/STAGES.md) for the expected output of every stage and
suggested talking points.

## The demo issues

| Issue | What the recorded agent does |
|---|---|
| `001-discount-case` | Gets it right first time |
| `002-bulk-pricing` | Off-by-one on the first try (`>` instead of `>=`), fixed on retry |
| `003-tax-rounding` | Changes the return type and rewrites an existing test to match; then uses `round()`, which passes the tests but violates the "round half up" requirement; then gets it right |

Each issue has human-written acceptance tests in `issues/<id>/acceptance_test.py`.
The factory installs them after every agent attempt, so the agent cannot weaken them.

## Using a real coding agent

Set `mode = "cli"` under `[agent]` and `[review]` in `factory.toml` and point `command`
at your agent. If no part of the command contains `{prompt}`, the prompt is sent on
stdin. If the agent prints JSON with `result` and `total_cost_usd` fields, the factory
records the cost.

```toml
[agent]
mode = "cli"
command = ["claude", "-p", "--output-format", "json", "--permission-mode", "acceptEdits"]
# command = ["codex", "exec", "--full-auto", "-"]
```

Check these flags against the version of your agent CLI. Reviewers should run with
read-only tools; the factory also rejects any review that changes the worktree.

To work on a real repository, point `[target] repo` at it. For GitHub issues and PRs,
set `[intake] source = "github"` and `[pr] mode = "github"` (requires the `gh` CLI).

## Layout

```
factory/
  orchestrator.py   the deterministic skeleton
  intake.py         issue -> Issue
  sandbox.py        git worktree per issue
  context.py        prompts from templates
  agent.py          CLI agent runner and replay
  gates.py          tests, lint, protected paths, acceptance tests
  review.py         reviewer panel with JSON validation, fails closed
  pr.py             commit, draft PR, or park for a human
  state.py          SQLite runs, attempts and cost report
prompts/            prompt templates
issues/             demo issues with acceptance tests
replays/            recorded agent patches and review verdicts
sample_project/     the small codebase the factory works on
```

## Design rules this code follows

1. **Code owns control flow.** Agents never decide what happens next.
2. **Exit codes, not opinions.** A gate passes when the checks pass, not when the agent says so.
3. **Humans own the spec.** Acceptance tests and existing tests are protected.
4. **Fail closed.** Unparseable review output is a rejection.
5. **Judgement merges in code.** Reviewers report; a rule decides.
6. **Every attempt costs money.** Failed runs count towards cost per accepted PR.
7. **A human merges.** The factory only opens drafts.
