"""Runtime configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FALLBACK_NOTICE = (
    "GROQ_API_KEY nao configurada. O pipeline foi executado em modo deterministico."
)


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    model_provider: str
    model_id: str
    groq_api_key: str | None
    database_path: Path
    knowledge_base_path: Path
    use_llm_agents: bool


def load_settings() -> Settings:
    """Load application settings without exposing secrets in source code."""

    load_dotenv(PROJECT_ROOT / ".env", override=True)
    groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip() or None
    if groq_api_key == "your-groq-api-key":
        groq_api_key = None

    return Settings(
        model_provider=os.getenv("MODEL_PROVIDER", "groq"),
        model_id=os.getenv("MODEL_ID", "llama-3.3-70b-versatile"),
        groq_api_key=groq_api_key,
        database_path=Path(os.getenv("DATABASE_PATH", "storage/requirements.db")),
        knowledge_base_path=Path(
            os.getenv("KNOWLEDGE_BASE_PATH", "storage/knowledge_base")
        ),
        use_llm_agents=os.getenv("USE_LLM_AGENTS", "false").lower()
        in {"1", "true", "yes", "on"},
    )


def resolve_use_llm(
    use_llm: bool | None = None,
    settings: Settings | None = None,
) -> tuple[bool, str | None]:
    """Return effective LLM usage and an optional deterministic fallback notice."""

    current = settings or load_settings()
    requested = current.use_llm_agents if use_llm is None else use_llm
    if not requested:
        return False, None
    if not current.groq_api_key:
        return False, FALLBACK_NOTICE
    return True, None
