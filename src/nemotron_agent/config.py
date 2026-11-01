from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    model: str
    workspace: Path
    think: bool
    max_steps: int
    project_root: Path


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    _load_dotenv(project_root / ".env")

    workspace = Path(
        os.environ.get("NEMOTRON_WORKSPACE", str(project_root / "workspace"))
    )
    if not workspace.is_absolute():
        workspace = (project_root / workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    return Settings(
        ollama_host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        model=os.environ.get("NEMOTRON_MODEL", "nemotron-3-nano:4b"),
        workspace=workspace,
        think=_as_bool(os.environ.get("NEMOTRON_THINK", "true")),
        max_steps=int(os.environ.get("NEMOTRON_MAX_STEPS", "12")),
        project_root=project_root,
    )
