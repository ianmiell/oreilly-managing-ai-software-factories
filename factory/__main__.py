"""Command line: python -m factory <command>."""

import argparse
import shutil
import subprocess

from factory import config, intake, orchestrator


def setup(cfg) -> None:
    """Create a fresh target repo from sample_project/."""
    target = cfg.path(cfg["target"]["repo"])
    if target.exists():
        raise SystemExit(f"{target} already exists. Run `uv run python -m factory reset` first.")
    shutil.copytree(cfg.root / "sample_project", target)
    git = ["git", "-c", "user.name=factory", "-c", "user.email=factory@localhost"]
    subprocess.run([*git, "init", "-q", "-b", cfg["target"]["base_branch"]], cwd=target, check=True)
    subprocess.run([*git, "add", "-A"], cwd=target, check=True)
    subprocess.run([*git, "commit", "-qm", "Initial commit"], cwd=target, check=True)
    print(f"Demo target repo ready at {target}")


def reset(cfg) -> None:
    for rel in (".demo", ".factory"):
        shutil.rmtree(cfg.root / rel, ignore_errors=True)
    print("Removed .demo/ and .factory/")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m factory")
    parser.add_argument("--config", help="path to factory.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="create the demo target repo")
    sub.add_parser("reset", help="delete demo repo, worktrees and state")
    run_p = sub.add_parser("run", help="run the factory on one issue")
    run_p.add_argument("issue", help="issue id prefix, e.g. 001, or a GitHub issue number")
    sub.add_parser("run-all", help="run every local issue in order")
    sub.add_parser("report", help="show runs and cost per accepted PR")
    acc = sub.add_parser("accept", help="record that a human merged an issue's PR")
    acc.add_argument("issue")
    args = parser.parse_args()
    cfg = config.load(args.config)

    if args.command == "setup":
        setup(cfg)
    elif args.command == "reset":
        reset(cfg)
    elif args.command == "run":
        orchestrator.run(cfg, args.issue)
    elif args.command == "run-all":
        for ref in intake.all_refs(cfg):
            orchestrator.run(cfg, ref)
            print()
    elif args.command in ("report", "accept"):
        from factory.state import Store
        store = Store(cfg)
        if args.command == "report":
            print(store.report())
        elif store.accept(args.issue):
            print(f"Marked {args.issue} as merged.")
        else:
            print(f"No opened PR found for {args.issue}.")


if __name__ == "__main__":
    main()
