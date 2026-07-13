from pathlib import Path
import shutil

from req_multiagent.ingestion.vector_store import (
    clear_knowledge_base,
    query_knowledge_base,
    rebuild_knowledge_base,
)


TEST_INDEX_PATH = Path("storage/test_vector_store")


def setup_function() -> None:
    clear_knowledge_base(TEST_INDEX_PATH)


def teardown_function() -> None:
    if TEST_INDEX_PATH.exists():
        shutil.rmtree(TEST_INDEX_PATH)


def test_rebuild_knowledge_base_indexes_corpus_and_existing_requirements() -> None:
    documents = rebuild_knowledge_base(
        source_paths=[
            Path("docs/corpus"),
            Path("data/existing_requirements"),
        ],
        index_path=TEST_INDEX_PATH,
    )

    assert documents
    assert (TEST_INDEX_PATH / "documents.json").exists()
    assert any("iso29148_criteria.md" in item.source_path for item in documents)
    assert any("existing_requirements.md" in item.source_path for item in documents)


def test_query_knowledge_base_returns_ranked_evidence() -> None:
    rebuild_knowledge_base(
        source_paths=[
            Path("docs/corpus"),
            Path("data/existing_requirements"),
        ],
        index_path=TEST_INDEX_PATH,
    )

    results = query_knowledge_base(
        query="cancelamento pedidos pagos",
        index_path=TEST_INDEX_PATH,
        limit=3,
    )

    assert results
    assert results[0].score > 0
    assert any("cancelamento" in result.document.content.lower() for result in results)
