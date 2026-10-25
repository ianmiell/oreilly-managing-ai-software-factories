"""Stage 2: sandbox. Every issue gets its own git worktree and branch."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


def git(cwd, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.name=factory", "-c", "user.email=factory@localhost", *args],
        cwd=cwd, capture_output=True, text=True, check=check,
    )


@dataclass
class Worktree:
    path: Path
    branch: str
    base: str  # commit the branch started from
    repo: Path


def create(cfg, issue) -> Worktree:
    repo = cfg.path(cfg["target"]["repo"])
    if not (repo / ".git").exists():
        raise SystemExit(f"No target repo at {repo}. Run `uv run python -m factory setup` first.")
    base = git(repo, "rev-parse", cfg["target"]["base_branch"]).stdout.strip()
    branch = f"factory/{issue.slug}"
    path = cfg.path(cfg["target"]["worktrees_dir"]) / issue.slug
    # A rerun replaces the previous attempt at this issue.
    git(repo, "worktree", "remove", "--force", str(path), check=False)
    git(repo, "worktree", "prune", check=False)
    git(repo, "branch", "-D", branch, check=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "-b", branch, str(path), base)
    return Worktree(path, branch, base, repo)


def reset(wt: Worktree) -> None:
    git(wt.path, "reset", "--hard", wt.base)
    git(wt.path, "clean", "-fd")


def changed_files(wt: Worktree) -> list[tuple[str, list[str]]]:
    """(status letter, paths) for every change since the base commit."""
    git(wt.path, "add", "-A")
    out = git(wt.path, "diff", "--cached", "--name-status", wt.base).stdout
    changes = []
    for line in out.splitlines():
        parts = line.split("\t")
        changes.append((parts[0][0], parts[1:]))
    return changes


def diff(wt: Worktree) -> str:
    git(wt.path, "add", "-A")
    return git(wt.path, "diff", "--cached", wt.base).stdout


def commit(wt: Worktree, message: str) -> None:
    git(wt.path, "add", "-A")
    git(wt.path, "commit", "--allow-empty", "-m", message)


def remove(wt: Worktree) -> None:
    git(wt.repo, "worktree", "remove", "--force", str(wt.path), check=False)
