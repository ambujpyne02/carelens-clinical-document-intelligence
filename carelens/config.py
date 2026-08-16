"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str = "gpt-5.6-terra"
    enable_synthesis: bool = True
    demo_access_code: str = ""
    max_files: int = 4
    max_file_mb: int = 10
    max_total_mb: int = 30
    max_pdf_pages: int = 25
    max_text_chars: int = 50_000

    @classmethod
    def from_env(cls, *, require_key: bool = True) -> "Settings":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if require_key and not key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Copy .env.example to .env and add a key."
            )
        return cls(
            openai_api_key=key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-terra").strip(),
            enable_synthesis=_as_bool(os.getenv("OPENAI_SYNTHESIS"), True),
            demo_access_code=os.getenv("DEMO_ACCESS_CODE", "").strip(),
        )
