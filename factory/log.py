"""Console output, formatted so a live audience can follow each stage."""


def log(stage: str, message: str) -> None:
    print(f"[{stage:>9}] {message}", flush=True)


def block(text: str, limit: int = 1200) -> None:
    text = text.strip()
    if len(text) > limit:
        text = "..." + text[-limit:]
    for line in text.splitlines():
        print(f"{'':>12}| {line}", flush=True)
