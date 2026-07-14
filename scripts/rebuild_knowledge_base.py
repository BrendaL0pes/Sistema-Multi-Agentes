"""Rebuild the local requirements knowledge base."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from req_multiagent.config import load_settings
from req_multiagent.ingestion.vector_store import rebuild_knowledge_base


def main() -> None:
    """Rebuild the local knowledge base from repository-versioned sources."""

    settings = load_settings()
    documents = rebuild_knowledge_base(
        source_paths=[
            PROJECT_ROOT / "docs" / "corpus",
            PROJECT_ROOT / "data" / "existing_requirements",
        ],
        index_path=PROJECT_ROOT / settings.knowledge_base_path,
    )
    print(
        "Knowledge base rebuilt at "
        f"{settings.knowledge_base_path.as_posix()} with {len(documents)} chunks."
    )


if __name__ == "__main__":
    main()
