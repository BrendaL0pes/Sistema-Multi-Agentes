"""Local knowledge-base indexing and query helpers."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from req_multiagent.config import load_settings


@dataclass(frozen=True)
class KnowledgeDocument:
    """A document chunk stored in the local knowledge base."""

    id: str
    source_path: str
    content: str


@dataclass(frozen=True)
class KnowledgeSearchResult:
    """A scored query result from the local knowledge base."""

    document: KnowledgeDocument
    score: int


def clear_knowledge_base(index_path: Path | str | None = None) -> None:
    """Remove the local knowledge-base directory if it exists."""

    target_path = Path(index_path) if index_path else load_settings().knowledge_base_path
    if target_path.exists():
        shutil.rmtree(target_path)


def initialize_knowledge_base(index_path: Path | str | None = None) -> Path:
    """Create the local knowledge-base directory and return its path."""

    target_path = Path(index_path) if index_path else load_settings().knowledge_base_path
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


def create_chroma_client(index_path: Path | str | None = None):
    """Create a persistent ChromaDB client when ChromaDB is installed.

    The rest of this module uses a JSON index so tests remain deterministic.
    Future ingestion work can call this function to back the same documents
    with ChromaDB embeddings without changing higher-level modules.
    """

    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "ChromaDB is not installed. Install project dependencies before "
            "using the Chroma-backed knowledge base."
        ) from exc

    target_path = initialize_knowledge_base(index_path)
    return chromadb.PersistentClient(path=str(target_path))


def rebuild_knowledge_base(
    source_paths: list[Path | str],
    index_path: Path | str | None = None,
) -> list[KnowledgeDocument]:
    """Clear and rebuild the local knowledge base from repository documents."""

    target_path = Path(index_path) if index_path else load_settings().knowledge_base_path
    clear_knowledge_base(target_path)
    initialize_knowledge_base(target_path)
    return index_documents(source_paths=source_paths, index_path=target_path)


def index_documents(
    source_paths: list[Path | str],
    index_path: Path | str | None = None,
) -> list[KnowledgeDocument]:
    """Index text-like documents into a simple local JSON store.

    ChromaDB can be introduced behind this module without changing callers.
    The JSON index keeps tests and classroom demos deterministic even when
    model or embedding services are unavailable.
    """

    target_path = initialize_knowledge_base(index_path)
    documents: list[KnowledgeDocument] = []
    for source_path in source_paths:
        path = Path(source_path)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    documents.extend(_load_document_chunks(child))
        elif path.is_file():
            documents.extend(_load_document_chunks(path))

    _write_index(target_path, documents)
    return documents


def query_knowledge_base(
    query: str,
    index_path: Path | str | None = None,
    limit: int = 5,
) -> list[KnowledgeSearchResult]:
    """Query the local knowledge base using deterministic keyword scoring."""

    target_path = Path(index_path) if index_path else load_settings().knowledge_base_path
    documents = _read_index(target_path)
    query_terms = _tokenize(query)
    results: list[KnowledgeSearchResult] = []

    for document in documents:
        document_terms = _tokenize(document.content)
        score = sum(document_terms.count(term) for term in query_terms)
        if score > 0:
            results.append(KnowledgeSearchResult(document=document, score=score))

    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _load_document_chunks(path: Path) -> list[KnowledgeDocument]:
    content = path.read_text(encoding="utf-8")
    chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
    return [
        KnowledgeDocument(
            id=f"{path.stem}-{index + 1:03d}",
            source_path=path.as_posix(),
            content=chunk,
        )
        for index, chunk in enumerate(chunks)
    ]


def _write_index(index_path: Path, documents: list[KnowledgeDocument]) -> None:
    index_file = index_path / "documents.json"
    payload = [asdict(document) for document in documents]
    index_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_index(index_path: Path) -> list[KnowledgeDocument]:
    index_file = index_path / "documents.json"
    if not index_file.exists():
        return []
    payload = json.loads(index_file.read_text(encoding="utf-8"))
    return [KnowledgeDocument(**item) for item in payload]


def _tokenize(text: str) -> list[str]:
    return re_split_words(text.lower())


def re_split_words(text: str) -> list[str]:
    """Split words without adding a regex dependency to callers."""

    return re.findall(r"[\wÀ-ÿ]+", text)
