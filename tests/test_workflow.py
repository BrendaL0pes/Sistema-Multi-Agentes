import shutil
from pathlib import Path

from req_multiagent.config import FALLBACK_NOTICE, Settings, load_settings
from req_multiagent.models import MoscowPriority
from req_multiagent.orchestration.workflow import (
    run_requirements_workflow,
    run_requirements_workflow_from_text,
)
from req_multiagent.persistence.repository import RequirementsRepository

TEST_DATABASE_PATH = Path("storage/test_workflow/requirements.db")


def _settings_without_api_key(*, use_llm_agents: bool) -> Settings:
    current = load_settings()
    return Settings(
        model_provider=current.model_provider,
        model_id=current.model_id,
        groq_api_key=None,
        database_path=TEST_DATABASE_PATH,
        knowledge_base_path=current.knowledge_base_path,
        use_llm_agents=use_llm_agents,
    )


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
    assert len(result.report.ambiguities) == 1
    assert len(result.report.conflicts) == 1
    assert result.report.gaps == []
    assert len(result.report.priorities) == 4
    assert result.report.conflicts[0].conflicting_requirement_id == "REQ-EXIST-001"
    assert any(
        item.priority == MoscowPriority.WONT for item in result.report.priorities
    )
    assert any(
        item.priority == MoscowPriority.COULD for item in result.report.priorities
    )
    assert "TRANSCRIPT_01_CHECKOUT-003" in result.report_markdown
    assert "## Lacunas" in result.report_markdown
    assert "Nenhuma lacuna detectada" in result.report_markdown

    repository = RequirementsRepository(TEST_DATABASE_PATH)
    persisted_requirements = repository.list_requirements()
    assert len(persisted_requirements) == 4

    persisted_reports = repository.list_reports()
    loaded_report = repository.get_report(persisted_reports[0]["id"])
    assert loaded_report is not None
    assert loaded_report.id == result.report.id
    assert len(loaded_report.requirements) == 4
    assert len(loaded_report.conflicts) == 1
    assert loaded_report.gaps == []
    assert loaded_report.priorities


def test_workflow_detects_support_conflicts_and_gaps() -> None:
    result = run_requirements_workflow(
        transcript_path="data/synthetic_transcripts/transcript_02_support.md",
        database_path=TEST_DATABASE_PATH,
        persist=False,
        use_llm=False,
    )

    assert result.success
    assert result.report is not None
    assert len(result.report.ambiguities) == 1
    assert len(result.report.conflicts) == 1
    assert len(result.report.gaps) == 1
    assert result.report.gaps[0].requirement_id is None
    assert "## Lacunas" in result.report_markdown
    assert "Narrativa" in result.report_markdown


def test_workflow_detects_approvals_gaps_and_persists_them() -> None:
    result = run_requirements_workflow(
        transcript_path="data/synthetic_transcripts/transcript_03_approvals.md",
        database_path=TEST_DATABASE_PATH,
        use_llm=False,
    )

    assert result.success
    assert result.report is not None
    assert len(result.report.ambiguities) == 1
    assert result.report.conflicts == []
    assert len(result.report.gaps) == 2
    assert any(item.priority == MoscowPriority.MUST for item in result.report.priorities)

    loaded_report = RequirementsRepository(TEST_DATABASE_PATH).get_report(
        result.report.id
    )
    assert loaded_report is not None
    assert len(loaded_report.gaps) == 2


def test_workflow_falls_back_without_groq_api_key(monkeypatch) -> None:
    fake_settings = _settings_without_api_key(use_llm_agents=True)
    monkeypatch.setattr(
        "req_multiagent.config.load_settings",
        lambda: fake_settings,
    )
    monkeypatch.setattr(
        "req_multiagent.orchestration.workflow.load_settings",
        lambda: fake_settings,
    )

    result = run_requirements_workflow(
        transcript_path="data/synthetic_transcripts/transcript_01_checkout.md",
        database_path=TEST_DATABASE_PATH,
        persist=False,
    )

    assert result.success
    assert result.report is not None
    assert len(result.report.conflicts) == 1
    assert result.message == FALLBACK_NOTICE


def test_workflow_runs_by_default_without_api_key(monkeypatch) -> None:
    fake_settings = _settings_without_api_key(use_llm_agents=False)
    monkeypatch.setattr(
        "req_multiagent.config.load_settings",
        lambda: fake_settings,
    )
    monkeypatch.setattr(
        "req_multiagent.orchestration.workflow.load_settings",
        lambda: fake_settings,
    )

    result = run_requirements_workflow(
        transcript_path="data/synthetic_transcripts/transcript_01_checkout.md",
        database_path=TEST_DATABASE_PATH,
        persist=False,
    )

    assert result.success
    assert result.report is not None
    assert len(result.report.requirements) == 4
    assert result.message == ""


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
QA: Nao ficou claro se a resposta pode ser enviada automaticamente.
"""

    result = run_requirements_workflow_from_text(
        transcript_text=transcript_text,
        source_name="conversa_teste.txt",
        database_path=TEST_DATABASE_PATH,
        persist=False,
        use_llm=False,
    )

    assert result.success
    assert result.report is not None
    assert len(result.report.requirements) == 2
    assert result.report.requirements[0].source.source_path == "conversa_teste.txt"
    assert len(result.report.gaps) == 1
    assert "CONVERSA_TESTE-001" in result.report_markdown
    assert "## Lacunas" in result.report_markdown
