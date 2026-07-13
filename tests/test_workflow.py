import shutil
from pathlib import Path

from req_multiagent.orchestration.workflow import (
    run_requirements_workflow,
    run_requirements_workflow_from_text,
)
from req_multiagent.persistence.repository import RequirementsRepository

TEST_DATABASE_PATH = Path("storage/test_workflow/requirements.db")


def setup_function() -> None:
    if TEST_DATABASE_PATH.parent.exists():
        shutil.rmtree(TEST_DATABASE_PATH.parent)


def teardown_function() -> None:
    if TEST_DATABASE_PATH.parent.exists():
        shutil.rmtree(TEST_DATABASE_PATH.parent)


def test_workflow_creates_report_and_persists_requirements() -> None:
    result = run_requirements_workflow(
        transcript_path="data/synthetic_transcripts/transcript_01_checkout.md",
        database_path=TEST_DATABASE_PATH,
        use_llm=False,
    )

    assert result.success
    assert result.report is not None
    assert len(result.report.requirements) == 4
    assert result.report.ambiguities
    assert result.report.conflicts == []
    assert result.report.priorities
    assert "TRANSCRIPT_01_CHECKOUT-003" in result.report_markdown

    repository = RequirementsRepository(TEST_DATABASE_PATH)
    persisted_requirements = repository.list_requirements()
    assert len(persisted_requirements) == 4

    persisted_reports = repository.list_reports()
    loaded_report = repository.get_report(persisted_reports[0]["id"])
    assert loaded_report is not None
    assert loaded_report.id == result.report.id
    assert len(loaded_report.requirements) == 4
    assert loaded_report.priorities


def test_workflow_returns_clear_error_for_missing_transcript() -> None:
    result = run_requirements_workflow(
        transcript_path="data/synthetic_transcripts/missing.md",
        database_path=TEST_DATABASE_PATH,
    )

    assert not result.success
    assert result.error is not None
    assert "not found" in result.error
    assert not TEST_DATABASE_PATH.exists()


def test_workflow_accepts_pasted_transcript_text() -> None:
    transcript_text = """
Cliente: [RF] O sistema deve permitir cadastrar solicitacoes.
Gestor: [RNF] A resposta deve ser enviada rapidamente.
"""

    result = run_requirements_workflow_from_text(
        transcript_text=transcript_text,
        source_name="conversa_teste.txt",
        database_path=TEST_DATABASE_PATH,
        persist=False,
    )

    assert result.success
    assert result.report is not None
    assert len(result.report.requirements) == 2
    assert result.report.requirements[0].source.source_path == "conversa_teste.txt"
    assert "CONVERSA_TESTE-001" in result.report_markdown
