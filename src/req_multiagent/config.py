"""Runtime configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    model_provider: str
    model_id: str
    groq_api_key: str | None
    database_path: Path
    knowledge_base_path: Path


def load_settings() -> Settings:
    """Load application settings without exposing secrets in source code."""

    return Settings(
        model_provider=os.getenv("MODEL_PROVIDER", "groq"),
        model_id=os.getenv("MODEL_ID", "llama-3.3-70b-versatile"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        database_path=Path(os.getenv("DATABASE_PATH", "storage/requirements.db")),
        knowledge_base_path=Path(
            os.getenv("KNOWLEDGE_BASE_PATH", "storage/knowledge_base")
        ),
    )
