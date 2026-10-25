"""Run state lives in SQLite, not in any agent's context window."""

import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    issue TEXT NOT NULL,
    started REAL NOT NULL,
    finished REAL,
    outcome TEXT,          -- pr_opened | escalated
    pr TEXT,
    accepted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attempts (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    n INTEGER NOT NULL,
    stage TEXT NOT NULL,   -- where the attempt ended: agent | gates | review | done
    cost_usd REAL NOT NULL,
    seconds REAL NOT NULL,
    notes TEXT
);
"""


class Store:
    def __init__(self, cfg):
        path = cfg.path(cfg["state"]["db"])
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def start_run(self, issue) -> int:
        cur = self.db.execute("INSERT INTO runs (issue, started) VALUES (?, ?)", (issue.slug, time.time()))
        self.db.commit()
        return cur.lastrowid

    def record_attempt(self, run_id, n, stage, cost_usd, seconds, notes="") -> None:
        self.db.execute("INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?)",
                        (run_id, n, stage, cost_usd, seconds, notes[:2000]))
        self.db.commit()

    def finish_run(self, run_id, outcome, pr=None) -> None:
        self.db.execute("UPDATE runs SET finished = ?, outcome = ?, pr = ? WHERE id = ?",
                        (time.time(), outcome, pr, run_id))
        self.db.commit()

    def accept(self, issue_ref: str) -> bool:
        """Mark the latest opened PR for an issue as merged by a human."""
        row = self.db.execute(
            "SELECT id FROM runs WHERE issue LIKE ? AND outcome = 'pr_opened' ORDER BY id DESC LIMIT 1",
            (issue_ref + "%",)).fetchone()
        if row:
            self.db.execute("UPDATE runs SET accepted = 1 WHERE id = ?", row)
            self.db.commit()
        return bool(row)

    def report(self) -> str:
        rows = self.db.execute("""
            SELECT r.issue, r.outcome, r.accepted, COUNT(a.n), COALESCE(SUM(a.cost_usd), 0)
            FROM runs r LEFT JOIN attempts a ON a.run_id = r.id
            GROUP BY r.id ORDER BY r.id""").fetchall()
        if not rows:
            return "No runs yet."
        lines = [f"{'issue':<22}{'outcome':<12}{'merged':<8}{'attempts':<10}cost (USD)"]
        for issue, outcome, accepted, attempts, cost in rows:
            lines.append(f"{issue:<22}{outcome or 'running':<12}{'yes' if accepted else 'no':<8}{attempts:<10}{cost:.2f}")
        total = sum(r[4] for r in rows)
        opened = sum(1 for r in rows if r[1] == "pr_opened")
        merged = sum(1 for r in rows if r[2])
        lines.append("")
        lines.append(f"Total spend (all runs, including failures): {total:.2f} USD")
        lines.append(f"PRs opened: {opened}   PRs merged: {merged}")
        if opened:
            lines.append(f"Cost per opened PR:   {total / opened:.2f} USD")
        lines.append(f"Cost per accepted PR: {total / merged:.2f} USD" if merged
                     else "Cost per accepted PR: n/a (mark merges with `uv run python -m factory accept <issue>`)")
        return "\n".join(lines)
