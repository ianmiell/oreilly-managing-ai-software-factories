"""Step 1: intake. Turn an issue reference into an Issue."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Issue:
    id: str
    slug: str
    title: str
    body: str
    acceptance: Path | None


def load(cfg, ref: str) -> Issue:
    if cfg["intake"]["source"] == "github":
        return _from_github(cfg, ref)
    return _from_local(cfg, ref)


def _from_local(cfg, ref: str) -> Issue:
    issues_dir = cfg.path(cfg["intake"]["issues_dir"])
    matches = [p for p in sorted(issues_dir.iterdir()) if p.is_dir() and p.name.startswith(ref)]
    if len(matches) != 1:
        raise SystemExit(f"Expected one issue matching {ref!r} in {issues_dir}, found {len(matches)}.")
    folder = matches[0]
    lines = (folder / "issue.md").read_text().splitlines()
    acceptance = folder / "acceptance_test.py"
    return Issue(
        id=folder.name.split("-")[0],
        slug=folder.name,
        title=lines[0].lstrip("# ").strip(),
        body="\n".join(lines[1:]).strip(),
        acceptance=acceptance if acceptance.exists() else None,
    )


def _from_github(cfg, ref: str) -> Issue:
    proc = subprocess.run(
        ["gh", "issue", "view", ref, "--json", "number,title,body"],
        cwd=cfg.path(cfg["target"]["repo"]), capture_output=True, text=True, check=True,
    )
    data = json.loads(proc.stdout)
    number = str(data["number"])
    return Issue(id=number, slug=f"gh-{number}", title=data["title"], body=data["body"] or "", acceptance=None)


def all_refs(cfg) -> list[str]:
    issues_dir = cfg.path(cfg["intake"]["issues_dir"])
    return [p.name for p in sorted(issues_dir.iterdir()) if (p / "issue.md").exists()]
