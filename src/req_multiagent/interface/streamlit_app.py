"""Streamlit interface for the requirements multi-agent assistant."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import streamlit as st
from groq import Groq

from req_multiagent import config as config_module
from req_multiagent.orchestration import workflow as requirements_workflow
from req_multiagent.orchestration.consolidator_agent import render_report_markdown
from req_multiagent.persistence import repository as repository_module

ACCEPTED_EXTENSIONS = (".md", ".txt")


def main() -> None:
    """Render the Streamlit application."""

    st.set_page_config(
        page_title="ReqLens",
        page_icon="RL",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_base_style()

    importlib.reload(config_module)
    settings = config_module.load_settings()
    importlib.reload(repository_module)
    repository = repository_module.RequirementsRepository(settings.database_path)
    persist = _render_sidebar(repository)

    _render_header()
    input_payload = _render_input_area()

    run_clicked = st.button(
        "Analisar conversa",
        type="primary",
        use_container_width=True,
        disabled=input_payload is None,
    )

    if run_clicked and input_payload:
        with st.spinner("Executando agentes de requisitos..."):
            _reload_pipeline_modules()
            result = _run_analysis(input_payload, persist=persist, use_llm=True)
        st.session_state["workflow_result"] = result

    result = st.session_state.get("workflow_result")
    if result is None:
        _render_empty_state()
        return

    if not result.success:
        st.error(result.error or "Nao foi possivel executar a analise.")
        return

    _render_result(result)


def _render_sidebar(repository) -> bool:
    st.sidebar.title("ReqLens")
    st.sidebar.caption("Assistente multiagente para Engenharia de Requisitos")

    st.sidebar.divider()
    if st.sidebar.button("Nova analise", use_container_width=True):
        st.session_state.pop("workflow_result", None)
        st.session_state["input_reset_counter"] = (
            st.session_state.get("input_reset_counter", 0) + 1
        )
        st.rerun()

    persist = st.sidebar.toggle("Salvar no historico", value=True)

    st.sidebar.divider()
    _render_history(repository)

    st.sidebar.divider()
    if st.sidebar.button("Limpar historico SQLite", use_container_width=True):
        repository.reset()
        st.session_state.pop("workflow_result", None)
        st.sidebar.success("Historico local limpo.")
        st.rerun()

    with st.sidebar.expander("Diagnostico"):
        st.caption(f"Python: {sys.executable}")

    return persist


def _render_history(repository) -> None:
    st.sidebar.subheader("Historico")
    reports = repository.list_reports()
    if not reports:
        st.sidebar.caption("Nenhuma analise salva ainda.")
        return

    report_options = {
        _format_report_option(report): report["id"]
        for report in reports
    }
    selected_label = st.sidebar.selectbox(
        "Analises salvas",
        options=list(report_options.keys()),
    )
    if st.sidebar.button("Abrir analise", use_container_width=True):
        if not hasattr(repository, "get_report"):
            st.sidebar.error(
                "Modulo de historico desatualizado. Reinicie o Streamlit."
            )
            return
        report = repository.get_report(report_options[selected_label])
        if report is None:
            st.sidebar.error("Analise nao encontrada.")
            return
        st.session_state["workflow_result"] = requirements_workflow.WorkflowRunResult(
            success=True,
            report=report,
            report_markdown=render_report_markdown(report),
        )
        st.rerun()


def _render_header() -> None:
    st.title("Analise de Requisitos")
    st.caption(
        "Cole ou importe uma conversa de stakeholders para extrair requisitos, "
        "ambiguidades, conflitos e prioridades MoSCoW."
    )

    steps = st.columns(4)
    steps[0].info("1. Informe a conversa")
    steps[1].info("2. Execute a analise")
    steps[2].info("3. Revise os achados")
    steps[3].info("4. Reabra pelo historico")


def _render_input_area() -> dict[str, Any] | None:
    reset_counter = st.session_state.get("input_reset_counter", 0)

    with st.container(border=True):
        st.subheader("Nova conversa")
        analysis_name = st.text_input(
            "Nome da analise ou projeto",
            placeholder="Exemplo: Portal de pedidos - aprovacao",
            key=f"analysis_name_{reset_counter}",
        )

        input_mode = st.radio(
            "Tipo de entrada",
            options=["Colar conversa", "Importar arquivo"],
            horizontal=True,
            key=f"input_mode_{reset_counter}",
        )

        if input_mode == "Colar conversa":
            return _render_paste_input(analysis_name, reset_counter)
        return _render_upload_input(analysis_name, reset_counter)


def _render_paste_input(
    analysis_name: str,
    reset_counter: int,
) -> dict[str, Any] | None:
    transcript_text = st.text_area(
        "Conversa do stakeholder",
        height=260,
        placeholder=(
            "Cliente: Quando o pedido ultrapassar o limite, ele precisa "
            "aguardar aprovacao.\n"
            "Gestor: Eu preciso ser avisado quando houver pedido pendente.\n"
            "Gestor: A notificacao precisa aparecer rapidamente."
        ),
        key=f"transcript_text_{reset_counter}",
    )
    st.caption(
        "A conversa pode ser natural. Marcadores [RF] e [RNF] sao opcionais."
    )
    if not transcript_text.strip():
        return None
    return {
        "kind": "text",
        "text": transcript_text,
        "source_name": _build_source_name(analysis_name, "conversa_colada", ".md"),
    }


def _render_upload_input(
    analysis_name: str,
    reset_counter: int,
) -> dict[str, Any] | None:
    uploaded_file = st.file_uploader(
        "Arquivo com a conversa",
        type=[extension.removeprefix(".") for extension in ACCEPTED_EXTENSIONS],
        accept_multiple_files=False,
        help="Formatos aceitos: .md e .txt",
        key=f"uploaded_file_{reset_counter}",
    )
    st.caption("Formatos aceitos: .md e .txt, preferencialmente em UTF-8.")

    if uploaded_file is None:
        return None

    transcript_text = _decode_uploaded_file(uploaded_file.getvalue())
    if not transcript_text.strip():
        st.warning("O arquivo importado esta vazio.")
        return None

    return {
        "kind": "text",
        "text": transcript_text,
        "source_name": _build_source_name(
            analysis_name,
            Path(uploaded_file.name).stem,
            Path(uploaded_file.name).suffix,
        ),
    }


def _run_analysis(input_payload: dict[str, Any], persist: bool, use_llm: bool):
    if use_llm:
        _assert_groq_connection()
    return requirements_workflow.run_requirements_workflow_from_text(
        transcript_text=input_payload["text"],
        source_name=input_payload["source_name"],
        persist=persist,
        use_llm=use_llm,
    )


def _assert_groq_connection() -> None:
    settings = config_module.load_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada no .env.")

    try:
        client = Groq(api_key=settings.groq_api_key, timeout=10, max_retries=0)
        client.chat.completions.create(
            model=settings.model_id,
            messages=[{"role": "user", "content": "Responda apenas OK"}],
            temperature=0,
            max_tokens=4,
        )
    except Exception as exc:
        raise RuntimeError(
            "Falha no teste de conexao com a Groq a partir do processo Streamlit: "
            f"{exc.__class__.__name__}: {exc}"
        ) from exc


def _render_empty_state() -> None:
    with st.container(border=True):
        st.subheader("Nenhuma analise aberta")
        st.write(
            "Informe uma conversa e clique em **Analisar conversa**, ou abra "
            "uma analise salva no historico da barra lateral."
        )


def _render_result(result) -> None:
    report = result.report
    if report is None:
        st.warning("Nenhum relatorio foi produzido.")
        return

    st.divider()
    st.subheader(report.title)
    st.caption(report.summary)

    metrics = st.columns(4)
    metrics[0].metric("Requisitos", len(report.requirements))
    metrics[1].metric("Ambiguidades", len(report.ambiguities))
    metrics[2].metric("Conflitos", len(report.conflicts))
    metrics[3].metric("Prioridades", len(report.priorities))

    tabs = st.tabs(
        ["Requisitos", "Ambiguidades", "Conflitos", "Priorizacao", "Relatorio"]
    )
    with tabs[0]:
        _render_requirements_table(report)
    with tabs[1]:
        _render_ambiguities(report)
    with tabs[2]:
        _render_conflicts(report)
    with tabs[3]:
        _render_priorities(report)
    with tabs[4]:
        st.markdown(result.report_markdown)


def _render_requirements_table(report) -> None:
    if not report.requirements:
        st.info("Nenhum requisito extraido.")
        return
    st.dataframe(
        [
            {
                "ID": item.id,
                "Tipo": item.type.value,
                "Descricao": item.description,
                "Fonte": item.source.source_path,
            }
            for item in report.requirements
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_ambiguities(report) -> None:
    if not report.ambiguities:
        st.success("Nenhuma ambiguidade detectada.")
        return

    for finding in report.ambiguities:
        with st.container(border=True):
            st.markdown(f"**{finding.requirement_id}**")
            st.write(f"Termo: `{finding.term}`")
            st.write(finding.explanation)
            if finding.clarification_questions:
                st.caption(f"Pergunta: {finding.clarification_questions[0]}")


def _render_conflicts(report) -> None:
    if not report.conflicts:
        st.success("Nenhum conflito detectado.")
        return

    for finding in report.conflicts:
        with st.container(border=True):
            conflicting_label = finding.conflicting_requirement_id
            if conflicting_label.startswith("REQ-EXIST-"):
                conflicting_label = f"{conflicting_label} (base existente)"
            st.markdown(
                f"**{finding.requirement_id}** x "
                f"**{conflicting_label}**"
            )
            st.write(finding.explanation)


def _render_priorities(report) -> None:
    if not report.priorities:
        st.info("Nenhuma prioridade gerada.")
        return

    st.dataframe(
        [
            {
                "Requisito": item.requirement_id,
                "Prioridade": item.priority.value,
                "Justificativa": item.rationale,
                "Limitacoes": "; ".join(item.limitations),
            }
            for item in report.priorities
        ],
        use_container_width=True,
        hide_index=True,
    )


def _decode_uploaded_file(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _build_source_name(label: str, fallback_stem: str, suffix: str) -> str:
    source_stem = label.strip() or fallback_stem
    safe_stem = "".join(
        character.lower() if character.isalnum() else "_"
        for character in source_stem
    ).strip("_")
    return f"{safe_stem or fallback_stem}{suffix}"


def _format_report_option(report: dict[str, Any]) -> str:
    created_at = report["created_at"].replace("T", " ")[:19]
    title = report["title"].replace("Relatorio de requisitos - ", "")
    return f"{created_at} | {title}"


def _reload_pipeline_modules() -> None:
    module_names = [
        "req_multiagent.config",
        "req_multiagent.llm_utils",
        "req_multiagent.ingestion.extractor_agent",
        "req_multiagent.analysis.ambiguity_agent",
        "req_multiagent.analysis.conflict_agent",
        "req_multiagent.analysis.prioritization_agent",
        "req_multiagent.orchestration.consolidator_agent",
    ]
    for module_name in module_names:
        importlib.reload(importlib.import_module(module_name))
    importlib.reload(requirements_workflow)


def _inject_base_style() -> None:
    st.markdown(
        """
        <style>
        :root {
          color-scheme: light;
        }
        html,
        body,
        .stApp {
          background: #f7f8fa !important;
          color: #111827 !important;
        }
        [data-testid="stAppViewContainer"] {
          background: #f7f8fa !important;
          color: #111827 !important;
        }
        [data-testid="stHeader"] {
          background: #111827 !important;
        }
        .main,
        .main p,
        .main span,
        .main label,
        .main h1,
        .main h2,
        .main h3,
        .main h4,
        .main li,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] *,
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] * {
          color: #111827 !important;
        }
        [data-testid="stSidebar"] {
          background: #ffffff !important;
          border-right: 1px solid #d1d5db;
        }
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] summary,
        [data-testid="stSidebar"] div {
          color: #111827 !important;
        }
        .main .block-container {
          max-width: 1180px;
          padding-top: 2rem;
          padding-bottom: 3rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
          background: #ffffff !important;
          border-color: #d1d5db !important;
        }
        div[data-testid="stMetric"] {
          background: #ffffff !important;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          padding: 0.75rem 1rem;
        }
        input,
        textarea,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] > div {
          background: #ffffff !important;
          color: #111827 !important;
          border-color: #9ca3af !important;
          -webkit-text-fill-color: #111827 !important;
        }
        input::placeholder,
        textarea::placeholder {
          color: #6b7280 !important;
          opacity: 1 !important;
          -webkit-text-fill-color: #6b7280 !important;
        }
        textarea,
        code,
        pre {
          font-family: Consolas, "Courier New", monospace;
        }
        button[kind="primary"],
        button[kind="primary"] * {
          background: #0f766e !important;
          border-color: #0f766e !important;
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }
        button[kind="secondary"],
        button[kind="secondary"] * {
          color: #111827 !important;
          -webkit-text-fill-color: #111827 !important;
        }
        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] span,
        div[data-testid="stAlert"] div {
          color: #111827 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
