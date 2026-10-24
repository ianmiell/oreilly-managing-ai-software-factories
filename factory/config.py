"""Load factory.toml and expand command templates."""

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "factory.toml"


@dataclass
class Config:
    raw: dict
    root: Path

    def __getitem__(self, key):
        return self.raw[key]

    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else (self.root / p).resolve()


def load(path: str | None = None) -> Config:
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return Config(raw, path.resolve().parent)


def expand(command: list[str], **values) -> list[str]:
    """Fill {placeholders} in a command template. {python} is always available."""
    values.setdefault("python", sys.executable)
    return [part.format(**values) if "{" in part else part for part in command]
