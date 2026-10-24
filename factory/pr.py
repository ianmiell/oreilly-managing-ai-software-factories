"""Stage 7: hand off. Commit, then open a draft PR. A human always merges."""

import subprocess

from factory import sandbox


def open_draft(cfg, wt, issue, summary: str) -> str:
    sandbox.commit(wt, f"{issue.title}\n\nOpened by the software factory for {issue.slug}.")
    if cfg["pr"]["mode"] == "github":
        sandbox.git(wt.path, "push", "-u", "origin", wt.branch)
        proc = subprocess.run(
            ["gh", "pr", "create", "--draft", "--title", issue.title, "--body-file", "-",
             "--head", wt.branch],
            cwd=wt.path, input=summary, capture_output=True, text=True, check=True,
        )
        return proc.stdout.strip()
    out_dir = cfg.path(cfg["pr"]["local_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{issue.slug}.md"
    path.write_text(summary)
    return str(path)


def park(wt, issue, reason: str) -> None:
    """Keep the work on its branch so a human can pick it up."""
    sandbox.commit(wt, f"WIP (escalated): {issue.title}\n\n{reason}")
