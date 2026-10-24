"""Stage 3: context. Build prompts from templates; nothing is improvised."""

from string import Template


def _template(cfg, name: str) -> Template:
    return Template((cfg.path(cfg["prompts_dir"]) / name).read_text())


def conventions(wt) -> str:
    path = wt.path / "AGENTS.md"
    return path.read_text().strip() if path.exists() else "(none)"


def _common(issue, wt) -> dict:
    return {
        "title": issue.title,
        "body": issue.body,
        "acceptance": issue.acceptance.read_text().strip() if issue.acceptance else "# none provided",
        "conventions": conventions(wt),
    }


def implement_prompt(cfg, issue, wt) -> str:
    return _template(cfg, "implement.md").substitute(_common(issue, wt))


def retry_prompt(cfg, issue, wt, feedback: str, attempt: int) -> str:
    return _template(cfg, "retry.md").substitute(
        _common(issue, wt), feedback=feedback, attempt=attempt,
        max_attempts=cfg["retry"]["max_attempts"],
    )
