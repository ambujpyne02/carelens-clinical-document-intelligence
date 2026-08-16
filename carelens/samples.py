"""Synthetic sample case discovery and loading."""

from __future__ import annotations

import json
from pathlib import Path

from .config import PROJECT_ROOT, Settings
from .ingestion import load_document
from .schemas import DocumentInput


MANIFEST_PATH = PROJECT_ROOT / "sample_data" / "manifest.json"


def sample_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"cases": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_sample_case(case_id: str, settings: Settings) -> list[DocumentInput]:
    manifest = sample_manifest()
    try:
        case = manifest["cases"][case_id]
    except KeyError as exc:
        raise KeyError(f"Unknown synthetic case: {case_id}") from exc
    return [
        load_document(PROJECT_ROOT / relative_path, settings)
        for relative_path in case["files"]
    ]

