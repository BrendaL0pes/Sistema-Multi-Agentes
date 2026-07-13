from pathlib import Path

from req_multiagent.ingestion.extractor_agent import (
    extract_requirements_from_file,
    extract_requirements_from_text,
)
from req_multiagent.models import RequirementType


def test_extractor_returns_structured_traceable_requirements() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    requirements = extract_requirements_from_file(transcript_path)

    assert len(requirements) == 4
    assert requirements[0].id == "TRANSCRIPT_01_CHECKOUT-001"
    assert requirements[0].type == RequirementType.FUNCTIONAL
    assert requirements[0].source.source_path == transcript_path.as_posix()
    assert requirements[0].source.excerpt.startswith("- [RF]")
    assert requirements[0].source.start_line is not None


def test_extractor_classifies_non_functional_requirements() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    requirements = extract_requirements_from_file(transcript_path)

    non_functional = [
        requirement
        for requirement in requirements
        if requirement.type == RequirementType.NON_FUNCTIONAL
    ]
    assert len(non_functional) == 1
    assert "pida" in non_functional[0].description


def test_extractor_handles_natural_stakeholder_conversation() -> None:
    transcript = """
Analista: Bom dia, queria entender o fluxo de pedidos.
Cliente: Quando o pedido ultrapassar o limite, ele precisa ficar parado aguardando aprovacao do gestor.
Gestor: Eu preciso ser avisado quando isso acontecer.
Gestor: A notificacao precisa aparecer rapidamente.
Cliente: O sistema deve guardar se o pedido foi aprovado ou reprovado.
Gestor: So gestor pode aprovar pedido pendente.
Analista: Essa tela precisa mostrar quais informacoes?
Gestor: Seria bom termos uma tela com os pedidos aguardando aprovacao.
"""

    requirements = extract_requirements_from_text(
        transcript=transcript,
        source_path="conversa_livre.txt",
        id_prefix="CONVERSA_LIVRE",
    )

    assert len(requirements) == 6
    assert requirements[0].id == "CONVERSA_LIVRE-001"
    assert requirements[0].type == RequirementType.FUNCTIONAL
    assert requirements[2].type == RequirementType.NON_FUNCTIONAL
    assert all(
        requirement.metadata["extraction_mode"] == "natural_language_heuristic"
        for requirement in requirements
    )
