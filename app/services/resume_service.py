from __future__ import annotations

import hashlib

from app.core.config import settings


def load_resume_text() -> str:
    resume_path = settings.resolved_resume_path
    if not resume_path.exists():
        raise FileNotFoundError(f"Resume file not found: {resume_path}")
    return resume_path.read_text(encoding="utf-8").strip()


def compute_resume_hash(resume_text: str) -> str:
    return hashlib.sha256(resume_text.encode("utf-8")).hexdigest()


def load_resume_payload() -> tuple[str, str]:
    resume_text = load_resume_text()
    return resume_text, compute_resume_hash(resume_text)