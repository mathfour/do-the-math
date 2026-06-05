"""Runtime configuration and API-key resolution.

The Anthropic key reaches the backend two ways: the per-request ``X-Anthropic-Key``
header (entered in the UI, stored in the browser) or the ``ANTHROPIC_API_KEY`` env
var (a dev/live-testing fallback from a gitignored ``.env``). The header wins.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # load backend/.env if present (gitignored)

DEFAULT_MODEL = "claude-sonnet-4-6"


@dataclass(frozen=True)
class Settings:
    model: str
    env_api_key: str | None
    cors_origins: tuple[str, ...]


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Settings(
        model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
        env_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
    )


def resolve_api_key(header_key: str | None, settings: Settings) -> str | None:
    """Header key takes precedence; fall back to the env key."""
    return (header_key or "").strip() or settings.env_api_key
