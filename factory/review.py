"""Stage 6: review. A panel of LLM reviewers, run in parallel, merged by code."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from factory import agent, context, sandbox

SEVERITIES = {"blocker", "minor"}


@dataclass
class Verdict:
    reviewer: str
    approve: bool
    issues: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    error: str | None = None


@dataclass
class PanelResult:
    approve: bool
    verdicts: list[Verdict]


def run_panel(cfg, wt, issue, attempt: int) -> PanelResult:
    diff = sandbox.diff(wt)
    reviewers = cfg["review"]["reviewers"]
    with ThreadPoolExecutor(max_workers=len(reviewers)) as pool:
        verdicts = list(pool.map(lambda r: review_one(cfg, wt, issue, attempt, r, diff), reviewers))

    # Reviewers must not change the code they are judging.
    if sandbox.diff(wt) != diff:
        verdicts.append(Verdict("factory", False, error="A reviewer modified the worktree."))

    # The merge rule lives in code: every reviewer must approve.
    return PanelResult(approve=all(v.approve for v in verdicts), verdicts=verdicts)


def review_one(cfg, wt, issue, attempt: int, reviewer: str, diff: str) -> Verdict:
    cost = 0.0
    if cfg["review"]["mode"] == "replay":
        path = cfg.path(cfg["agent"]["replays_dir"]) / issue.slug / f"review-{reviewer}-attempt-{attempt}.json"
        if not path.exists():
            return Verdict(reviewer, False, error=f"No recorded review at {path}.")
        text = path.read_text()
    else:
        prompt = context.review_prompt(cfg, issue, wt, reviewer, diff)
        result = agent.run_cli(cfg["review"]["command"], wt.path, prompt, cfg["review"]["timeout_seconds"])
        if not result.ok:
            return Verdict(reviewer, False, cost_usd=result.cost_usd, error=result.output[-500:])
        text, cost = result.output, result.cost_usd

    try:
        data = _extract_json(text)
        errors = validate(data)
    except ValueError as exc:
        errors = [str(exc)]
    if errors:
        # Fail closed: output we cannot parse is a rejection, not an approval.
        return Verdict(reviewer, False, cost_usd=cost, error="Invalid review output: " + "; ".join(errors))

    # A reviewer that says "approve" while listing a blocker does not get the final word.
    has_blocker = any(i["severity"] == "blocker" for i in data["issues"])
    return Verdict(reviewer, data["approve"] and not has_blocker, data["issues"], cost)


def validate(data) -> list[str]:
    if not isinstance(data, dict):
        return ["expected a JSON object"]
    errors = []
    if not isinstance(data.get("approve"), bool):
        errors.append("'approve' must be true or false")
    issues = data.get("issues")
    if not isinstance(issues, list):
        return errors + ["'issues' must be a list"]
    for n, item in enumerate(issues):
        if not isinstance(item, dict):
            errors.append(f"issue {n} must be an object")
        elif item.get("severity") not in SEVERITIES:
            errors.append(f"issue {n} has invalid severity {item.get('severity')!r}")
        elif not isinstance(item.get("message"), str):
            errors.append(f"issue {n} needs a message")
    return errors


def _extract_json(text: str):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON: {exc}") from exc


def feedback(result: PanelResult) -> str:
    lines = []
    for v in result.verdicts:
        if v.error:
            lines.append(f"- [{v.reviewer}] {v.error}")
        for i in v.issues:
            lines.append(f"- [{v.reviewer}] {i['severity']}: {i.get('file', '')} {i['message']}".rstrip())
    return "Code review rejected the change:\n" + "\n".join(lines)
