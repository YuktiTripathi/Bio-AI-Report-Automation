"""Persist BioReport JSON by record_id (PDFs are regenerated on demand)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE_DIR = _REPO_ROOT / "storage" / "bioreports"

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


def store_dir() -> Path:
    path = Path(__import__("os").environ.get("BIOAI_REPORT_STORE", str(DEFAULT_STORE_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_record_id(raw: str) -> str:
    cleaned = _SAFE_ID.sub("_", (raw or "").strip())
    return cleaned[:120] or uuid.uuid4().hex


def resolve_record_id(payload: dict[str, Any]) -> str:
    patient = payload.get("patient") or {}
    meta = payload.get("report_metadata") or {}
    for candidate in (
        patient.get("record_id"),
        meta.get("record_id"),
        patient.get("profile_id"),
    ):
        if candidate and str(candidate).strip():
            return sanitize_record_id(str(candidate))
    return uuid.uuid4().hex


def json_path(record_id: str) -> Path:
    return store_dir() / f"{sanitize_record_id(record_id)}.json"


def save_report_json(payload: dict[str, Any], *, record_id: str | None = None) -> str:
    rid = sanitize_record_id(record_id or resolve_record_id(payload))
    path = json_path(rid)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return rid


def load_report_json(record_id: str) -> dict[str, Any] | None:
    path = json_path(record_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def exists(record_id: str) -> bool:
    return json_path(record_id).is_file()
