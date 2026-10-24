"""The deterministic skeleton. Every decision about what happens next is an `if` here."""

from factory import agent, context, gates, intake, pr, sandbox
from factory.log import block, log


def run(cfg, issue_ref: str) -> str:
    issue = intake.load(cfg, issue_ref)
    log("intake", f"{issue.slug}: {issue.title}")

    wt = sandbox.create(cfg, issue)
    log("sandbox", f"worktree {wt.path.name} on branch {wt.branch}")

    try:
        prompt = context.implement_prompt(cfg, issue, wt)
        log("agent", "attempt 1 ...")
        result = agent.run(cfg, wt, prompt, issue, 1)
        if not result.ok:
            log("agent", "FAILED")
            block(result.output)
            pr.park(wt, issue, result.output)
            log("escalate", f"work parked on {wt.branch} for a human")
            return "escalated"
        log("agent", f"done in {result.seconds:.0f}s, {result.cost_usd:.2f} USD: {result.output}")

        gate = gates.run(cfg, wt, issue)
        for name, ok in gate.checks:
            log("gate", f"{'PASS' if ok else 'FAIL'}  {name}")
        if not gate.passed:
            block(gate.report)
            pr.park(wt, issue, gate.report)
            log("escalate", f"gates failed; work parked on {wt.branch} for a human")
            return "escalated"

        ref = pr.open_draft(cfg, wt, issue, _summary(issue, wt, result, gate))
        log("pr", f"draft PR ready: {ref}")
        return "pr_opened"
    finally:
        sandbox.remove(wt)


def _summary(issue, wt, result, gate) -> str:
    lines = [f"# {issue.title}", "", f"Branch: `{wt.branch}`  ", f"Issue: `{issue.slug}`", "",
             f"Agent summary: {result.output}", "", "## Checks", ""]
    lines += [f"- {'PASS' if ok else 'FAIL'}: {name}" for name, ok in gate.checks]
    lines += ["", "_Opened as a draft by the software factory. A human must review and merge._", ""]
    return "\n".join(lines)
