"""Step 4: implement. Run a coding agent, or replay a recorded run."""

import json
import subprocess
import time
from dataclasses import dataclass

from factory import sandbox
from factory.config import expand


@dataclass
class AgentResult:
    ok: bool
    output: str
    cost_usd: float = 0.0
    seconds: float = 0.0


def run(cfg, wt, prompt: str, issue, attempt: int) -> AgentResult:
    if cfg["agent"]["mode"] == "replay":
        return _replay(cfg, wt, issue, attempt)
    return run_cli(cfg["agent"]["command"], wt.path, prompt, cfg["agent"]["timeout_seconds"])


def run_cli(command: list[str], cwd, prompt: str, timeout: int) -> AgentResult:
    """Run any CLI agent. The prompt goes in {prompt} if present, otherwise on stdin."""
    as_arg = any("{prompt}" in part for part in command)
    cmd = expand(command, prompt=prompt) if as_arg else expand(command)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, check=False, cwd=cwd, input=None if as_arg else prompt,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return AgentResult(False, f"Agent timed out after {timeout}s.", seconds=timeout)
    except FileNotFoundError:
        return AgentResult(False, f"Agent command not found: {cmd[0]}")
    seconds = time.monotonic() - start
    text, cost = _parse_output(proc.stdout)
    if proc.returncode != 0:
        return AgentResult(False, (proc.stderr or text)[-4000:], cost, seconds)
    return AgentResult(True, text, cost, seconds)


def _parse_output(stdout: str) -> tuple[str, float]:
    """Agents with JSON output often report a result and a cost. Plain text is fine too."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout, 0.0
    if isinstance(data, dict):
        return str(data.get("result", stdout)), float(data.get("total_cost_usd") or 0.0)
    return stdout, 0.0


def _replay(cfg, wt, issue, attempt: int) -> AgentResult:
    folder = cfg.path(cfg["agent"]["replays_dir"]) / issue.slug
    patch = folder / f"attempt-{attempt}.patch"
    if not patch.exists():
        return AgentResult(False, f"No recorded run at {patch}.")
    meta_file = folder / "meta.json"
    meta = json.loads(meta_file.read_text()).get(f"attempt-{attempt}", {}) if meta_file.exists() else {}
    sandbox.reset(wt)  # recordings are full diffs against the base commit
    applied = sandbox.git(wt.path, "apply", str(patch), check=False)
    time.sleep(cfg["agent"].get("replay_delay_seconds", 0))
    if applied.returncode != 0:
        return AgentResult(False, f"Recorded patch did not apply: {applied.stderr}")
    return AgentResult(True, meta.get("summary", "(replayed)"), meta.get("cost_usd", 0.0), meta.get("seconds", 0.0))
