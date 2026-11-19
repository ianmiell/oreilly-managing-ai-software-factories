"""Step 5: gates. Code decides pass or fail; the agent's opinion is never asked."""

import shutil
import subprocess
from dataclasses import dataclass, field

from factory import sandbox
from factory.config import expand


@dataclass
class GateResult:
    passed: bool
    checks: list[tuple[str, bool]] = field(default_factory=list)
    report: str = ""


def run(cfg, wt, issue) -> GateResult:
    gates = cfg["gates"]
    checks, failures = [], []

    # 1. Protected paths: inspect the agent's own changes before anything else is added.
    violations = protected_violations(wt, gates["protected_paths"], gates["acceptance_dir"])
    checks.append(("protected paths", not violations))

    # 2. Human-written acceptance tests are installed fresh every attempt.
    install_acceptance(wt, issue, gates["acceptance_dir"])

    # 3. Every configured check runs; exit codes are the only signal.
    for command in gates["checks"]:
        cmd = expand(command)
        name = " ".join(command).replace("{python} -m ", "")
        try:
            proc = subprocess.run(cmd, check=False, cwd=wt.path, capture_output=True, text=True,
                                  timeout=gates["timeout_seconds"])
            ok, output = proc.returncode == 0, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            ok, output = False, f"timed out after {gates['timeout_seconds']}s"
        checks.append((name, ok))
        if not ok:
            failures.append(f"`{name}` failed:\n{output.strip()[-1500:]}")

    # Listed last so it is the first thing a reader (or the live audience) sees.
    if violations:
        failures.append("Modified or deleted protected files (not allowed):\n" + "\n".join(violations))

    return GateResult(passed=not failures, checks=checks, report="\n\n".join(failures))


def protected_violations(wt, protected: list[str], acceptance_dir: str) -> list[str]:
    violations = []
    for status, paths in sandbox.changed_files(wt):
        if status not in "MDR":  # added files are allowed
            continue
        for path in paths:
            if path.startswith(acceptance_dir):
                continue
            if any(path.startswith(prefix) for prefix in protected):
                violations.append(f"{status} {path}")
    return violations


def install_acceptance(wt, issue, acceptance_dir: str) -> None:
    if not issue.acceptance:
        return
    dest = wt.path / acceptance_dir / f"test_issue_{issue.id}.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(issue.acceptance, dest)
