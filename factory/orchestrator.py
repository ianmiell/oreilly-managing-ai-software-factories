"""The deterministic skeleton. Every decision about what happens next is an `if` here."""

from factory import agent, context, gates, intake, pr, sandbox
from factory.log import block, log


def run(cfg, issue_ref: str) -> str:
    issue = intake.load(cfg, issue_ref)
    log("intake", f"{issue.slug}: {issue.title}")

    wt = sandbox.create(cfg, issue)
    log("sandbox", f"worktree {wt.path.name} on branch {wt.branch}")

    max_attempts = cfg["retry"]["max_attempts"]
    prompt = context.implement_prompt(cfg, issue, wt)
    history = []

    try:
        for attempt in range(1, max_attempts + 1):
            log("agent", f"attempt {attempt}/{max_attempts} ...")
            result = agent.run(cfg, wt, prompt, issue, attempt)
            if not result.ok:
                log("agent", "FAILED")
                block(result.output)
                history.append((attempt, "agent failed", result.cost_usd))
                prompt = context.retry_prompt(cfg, issue, wt, f"The agent run failed:\n{result.output}", attempt)
                continue
            log("agent", f"done in {result.seconds:.0f}s, {result.cost_usd:.2f} USD: {result.output}")

            gate = gates.run(cfg, wt, issue)
            for name, ok in gate.checks:
                log("gate", f"{'PASS' if ok else 'FAIL'}  {name}")
            if not gate.passed:
                block(gate.report)
                history.append((attempt, "rejected by gates", result.cost_usd))
                # The failure output becomes the next prompt: the loop that makes agents useful.
                prompt = context.retry_prompt(cfg, issue, wt, gate.report, attempt)
                continue

            history.append((attempt, "accepted", result.cost_usd))
            ref = pr.open_draft(cfg, wt, issue, _summary(issue, wt, history))
            log("pr", f"draft PR ready: {ref}")
            return "pr_opened"

        pr.park(wt, issue, f"Gave up after {max_attempts} attempts.")
        log("escalate", f"no passing attempt; work parked on {wt.branch} for a human")
        return "escalated"
    finally:
        sandbox.remove(wt)


def _summary(issue, wt, history) -> str:
    lines = [f"# {issue.title}", "", f"Branch: `{wt.branch}`  ", f"Issue: `{issue.slug}`", "",
             "## Attempts", "", "| # | Result | Cost (USD) |", "|---|---|---|"]
    lines += [f"| {n} | {outcome} | {cost:.2f} |" for n, outcome, cost in history]
    lines += ["", "_Opened as a draft by the software factory. A human must review and merge._", ""]
    return "\n".join(lines)
