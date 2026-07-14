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
        page_icon="🔎",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_base_style()

    importlib.reload(config_module)
    settings = config_module.load_settings()
    importlib.reload(repository_module)
    repository = repository_module.RequirementsRepository(settings.database_path)
    persist, use_llm = _render_sidebar(repository)
    st.session_state["persist_history"] = persist
    st.session_state["use_llm"] = use_llm

    _render_header()
    input_payload = _render_input_area()

    run_clicked = st.button(
        "Analisar conversa",
        type="primary",
        width="stretch",
        disabled=input_payload is None,
    )

    if run_clicked and input_payload:
        with st.spinner("Executando agentes de requisitos..."):
            _reload_pipeline_modules()
            result = _run_analysis(input_payload, persist=persist, use_llm=use_llm)
        st.session_state["workflow_result"] = result

    result = st.session_state.get("workflow_result")
    if result is None:
        _render_empty_state()
        return

    if not result.success:
        st.error(result.error or "Nao foi possivel executar a analise.")
        return

    _render_result(result, repository, persist)


def _render_sidebar(repository) -> tuple[bool, bool]:
    st.sidebar.title("ReqLens")
    st.sidebar.caption("Assistente multiagente para Engenharia de Requisitos")

    st.sidebar.divider()
    if st.sidebar.button("➕ Nova análise", width="stretch"):
        st.session_state.pop("workflow_result", None)
        st.session_state["input_reset_counter"] = (
            st.session_state.get("input_reset_counter", 0) + 1
        )
        st.rerun()

    persist = st.sidebar.toggle("💾 Salvar no histórico", value=True)
    use_llm = st.sidebar.toggle("🤖 Usar LLM Groq", value=config_module.load_settings().use_llm_agents)

    st.sidebar.divider()
    _render_history(repository)

    st.sidebar.divider()
    if st.sidebar.button("🗑️ Limpar histórico SQLite", width="stretch"):
        repository.reset()
        st.session_state.pop("workflow_result", None)
        st.sidebar.success("Historico local limpo.")
        st.rerun()

    with st.sidebar.expander("Diagnostico"):
        st.caption(f"Python: {sys.executable}")

    return persist, use_llm


def _render_history(repository) -> None:
    st.sidebar.subheader("Histórico")
    reports = repository.list_reports()
    if not reports:
        st.sidebar.caption("Nenhuma análise salva ainda.")
        return

    report_options = {
        _format_report_option(report): report["id"]
        for report in reports
    }
    selected_label = st.sidebar.selectbox(
        "Análises salvas",
        options=list(report_options.keys()),
    )
    if st.sidebar.button("📂 Abrir análise", width="stretch"):
        if not hasattr(repository, "get_report"):
            st.sidebar.error(
                "Modulo de historico desatualizado. Reinicie o Streamlit."
            )
            return
        report = repository.get_report(report_options[selected_label])
        if report is None:
            st.sidebar.error("Análise não encontrada.")
            return
        st.session_state["workflow_result"] = requirements_workflow.WorkflowRunResult(
            success=True,
            report=report,
            report_markdown=render_report_markdown(report),
        )
        st.rerun()


def _render_header() -> None:
    st.markdown("""
    <div class="custom-header">
    <h1 style="margin:0; padding:0;">🔎 ReqLens</h1>
    <small style="font-size:15px;">Clareza para melhores requisitos</small>
    </div>
    """, unsafe_allow_html=True)
    st.caption(
        "Cole ou importe uma conversa de stakeholders para extrair requisitos, "
        "ambiguidades, conflitos e prioridades MoSCoW."
    )

    steps = st.columns(4)
    steps[0].info("1. Informe a conversa")
    steps[1].info("2. Execute a análise")
    steps[2].info("3. Revise os achados")
    steps[3].info("4. Reabra pelo histórico")


def _render_input_area() -> dict[str, Any] | None:
    reset_counter = st.session_state.get("input_reset_counter", 0)

    with st.container(border=True):
        st.subheader("Nova conversa")
        analysis_name = st.text_input(
            "Nome da análise ou projeto",
            placeholder="Exemplo: Portal de pedidos - aprovação",
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
            "aguardar aprovação.\n"
            "Gestor: Eu preciso ser avisado quando houver pedido pendente.\n"
            "Gestor: A notificação precisa aparecer rapidamente."
        ),
        key=f"transcript_text_{reset_counter}",
    )
    st.caption(
        "A conversa pode ser natural. Marcadores [RF] e [RNF] são opcionais."
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
        st.warning("O arquivo importado está vazio.")
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
        st.subheader("Nenhuma análise aberta")
        st.write(
            "Informe uma conversa e clique em **Analisar conversa**, ou abra "
            "uma análise salva no histórico da barra lateral."
        )


def _render_result(result, repository, persist: bool) -> None:
    report = result.report
    if report is None:
        st.warning("Nenhum relatório foi produzido.")
        return

    st.divider()
    st.subheader(report.title)
    st.caption(report.summary)

    req_count = len(report.requirements)
    amb_count = len(report.ambiguities)
    con_count = len(report.conflicts)
    prio_count = len(report.priorities)
    
    must_c = sum(1 for p in report.priorities if p.priority.value == "must")
    should_c = sum(1 for p in report.priorities if p.priority.value == "should")
    could_c = sum(1 for p in report.priorities if p.priority.value == "could")
    wont_c = sum(1 for p in report.priorities if p.priority.value == "wont")
    
    must_pct = int((must_c / prio_count) * 100) if prio_count else 0
    should_pct = int((should_c / prio_count) * 100) if prio_count else 0
    could_pct = int((could_c / prio_count) * 100) if prio_count else 0
    wont_pct = int((wont_c / prio_count) * 100) if prio_count else 0
    
    deg_must = (must_pct/100) * 360
    deg_should = (should_pct/100) * 360
    deg_could = (could_pct/100) * 360
    
    grad = f"conic-gradient(#ef4444 0deg {deg_must}deg, #f59e0b {deg_must}deg {deg_must+deg_should}deg, #3b82f6 {deg_must+deg_should}deg {deg_must+deg_should+deg_could}deg, #9ca3af {deg_must+deg_should+deg_could}deg 360deg)"

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-header">
                <div class="icon-wrapper blue-icon">📄</div>
                <div><div class="metric-value">{req_count}</div><div class="metric-label">Requisitos</div></div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <div class="icon-wrapper yellow-icon">⚠️</div>
                <div><div class="metric-value">{amb_count}</div><div class="metric-label">Ambiguidades</div></div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <div class="icon-wrapper red-icon">⚔️</div>
                <div><div class="metric-value">{con_count}</div><div class="metric-label">Conflitos</div></div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <div class="icon-wrapper green-icon">🎯</div>
                <div><div class="metric-value">{prio_count}</div><div class="metric-label">Prioridades</div></div>
            </div>
        </div>
    </div>
    
    <div class="moscow-container">
        <h3 style="margin-top:0;">Gráfico MoSCoW</h3>
        <div style="display:flex; align-items:center; gap:30px;">
            <div class="moscow-chart" style="background: {grad};"></div>
            <div class="moscow-legend">
                <div class="moscow-item"><span style="background:#ef4444;"></span>Must ({must_pct}%)</div>
                <div class="moscow-item"><span style="background:#f59e0b;"></span>Should ({should_pct}%)</div>
                <div class="moscow-item"><span style="background:#3b82f6;"></span>Could ({could_pct}%)</div>
                <div class="moscow-item"><span style="background:#9ca3af;"></span>Won't ({wont_pct}%)</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(
        [
            "Requisitos",
            "Ambiguidades",
            "Conflitos",
            "Priorização",
            "Adicionar conversa",
            "Ajustes",
            "Relatório",
        ]
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
        _render_increment_project(report, persist)
    with tabs[5]:
        _render_adjustment_chat(report, repository, persist)
    with tabs[6]:
        st.markdown(result.report_markdown)


def _render_requirements_table(report) -> None:
    if not report.requirements:
        st.info("Nenhum requisito extraído.")
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
        width="stretch",
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
        width="stretch",
        hide_index=True,
    )


def _render_increment_project(report, persist: bool) -> None:
    st.subheader("Adicionar conversa ao projeto")
    st.caption(
        "Cole ou importe uma nova parte da conversa. O agente compara com os "
        "requisitos atuais do projeto e cria ou atualiza requisitos."
    )

    mode = st.radio(
        "Entrada incremental",
        options=["Colar conversa", "Importar arquivo"],
        horizontal=True,
        key=f"increment_mode_{report.id}",
    )
    transcript_text = ""
    source_name = "incremento.md"

    if mode == "Colar conversa":
        transcript_text = st.text_area(
            "Nova conversa",
            height=180,
            key=f"increment_text_{report.id}",
        )
        source_name = "incremento_colado.md"
    else:
        uploaded_file = st.file_uploader(
            "Arquivo incremental",
            type=[extension.removeprefix(".") for extension in ACCEPTED_EXTENSIONS],
            key=f"increment_file_{report.id}",
        )
        if uploaded_file is not None:
            transcript_text = _decode_uploaded_file(uploaded_file.getvalue())
            source_name = uploaded_file.name

    if st.button(
        "Incrementar requisitos",
        type="primary",
        width="stretch",
        disabled=not transcript_text.strip(),
        key=f"increment_button_{report.id}",
    ):
        with st.spinner("Atualizando projeto com nova conversa..."):
            _reload_pipeline_modules()
            result = requirements_workflow.increment_requirements_project(
                report=report,
                transcript_text=transcript_text,
                source_name=source_name,
                persist=persist,
                use_llm=st.session_state.get("use_llm", True),
            )
        _handle_project_update_result(result)


def _render_adjustment_chat(report, repository, persist: bool) -> None:
    st.subheader("Chat com agente")
    st.caption(
        "Faça perguntas sobre a análise ou peça ajustes como unir, remover, "
        "reclassificar ou adicionar critérios."
    )
    for message in report.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_message = st.chat_input(
        "Pergunte algo ou peça um ajuste nos requisitos",
        key=f"adjustment_input_{report.id}",
    )
    if user_message:
        chat_messages = [
            *report.chat_messages,
            {"role": "user", "content": user_message},
        ]
        if _looks_like_question(user_message):
            with st.spinner("Consultando agente..."):
                _reload_pipeline_modules()
                result = requirements_workflow.answer_requirements_project_question(
                    report=report,
                    question=user_message,
                )
        else:
            with st.spinner("Aplicando ajuste no projeto..."):
                _reload_pipeline_modules()
                result = requirements_workflow.adjust_requirements_project(
                    report=report,
                    instruction=user_message,
                    persist=False,
                    use_llm=st.session_state.get("use_llm", True),
                )

        if result.success and result.report is not None:
            result.report.chat_messages = [
                *chat_messages,
                {
                    "role": "assistant",
                    "content": result.message or "Projeto atualizado.",
                },
            ]
            result.report_markdown = render_report_markdown(result.report)
            if persist:
                repository.save_report(result.report)
        _handle_project_update_result(result)


def _looks_like_question(message: str) -> bool:
    normalized = message.strip().lower()
    question_starters = (
        "por que",
        "porque",
        "qual",
        "quais",
        "como",
        "o que",
        "onde",
        "quando",
        "explique",
        "me explique",
    )
    return normalized.endswith("?") or normalized.startswith(question_starters)


def _handle_project_update_result(result) -> None:
    if not result.success:
        st.error(result.error or "Nao foi possivel atualizar o projeto.")
        return
    st.session_state["workflow_result"] = result
    if result.message:
        st.success(result.message)
    st.rerun()


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
        "req_multiagent.orchestration.project_update_agent",
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
        .custom-header {
            background: linear-gradient(90deg,#0f172a,#1e293b);
            padding: 18px 40px;
            border-radius: 18px;
            box-shadow: 0 8px 25px rgba(0,0,0,.15);
            border-bottom: 3px solid #3b82f6;
            margin-bottom: 20px;
        }
        .custom-header h1,
        .custom-header small,
        .custom-header * {
            color: #f3f4f6 !important;
            -webkit-text-fill-color: #f3f4f6 !important;
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
        [data-testid="stHeader"] * {
          color: #f3f4f6 !important;
          fill: #f3f4f6 !important;
        }
        [data-testid="stHeader"]::after {
          content: "ReqLens";
          position: absolute;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          color: #f3f4f6;
          font-size: 1.2rem;
          font-weight: 600;
          letter-spacing: 0.05em;
        }
        [data-testid="collapsedControl"],
        [data-testid="collapsedControl"] svg {
          color: #f3f4f6 !important;
          fill: #f3f4f6 !important;
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
        button[kind="secondary"] {
          background: #e8f4fd !important;
          border-color: transparent !important;
          justify-content: flex-start !important;
          padding-left: 15px !important;
          border-radius: 10px !important;
          transition: background 0.2s ease !important;
        }
        button[kind="secondary"]:hover {
          background: #dbeafe !important;
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
        .metric-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:15px; margin-bottom:20px; }
        .metric-card { background:white; padding:15px; border-radius:12px; border:1px solid #E5E7EB; box-shadow:0 4px 6px rgba(0,0,0,.05); }
        .metric-header { display:flex; align-items:center; gap:12px; }
        .icon-wrapper { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px; }
        .blue-icon { background:#EFF6FF; color:#3B82F6; }
        .yellow-icon { background:#FEF3C7; color:#D97706; }
        .red-icon { background:#FEE2E2; color:#DC2626; }
        .green-icon { background:#D1FAE5; color:#059669; }
        .metric-value { font-size:24px; font-weight:700; color:#111827; line-height:1; }
        .metric-label { font-size:13px; color:#6B7280; text-transform:uppercase; font-weight:600; margin-top:4px; }
        .moscow-container { background:white; padding:20px; border-radius:15px; border:1px solid #E5E7EB; margin-bottom:20px; box-shadow:0 4px 6px rgba(0,0,0,.05); }
        .moscow-chart { width:120px; height:120px; border-radius:50%; }
        .moscow-legend { display:flex; flex-direction:column; gap:8px; }
        .moscow-item { display:flex; align-items:center; gap:8px; font-size:14px; font-weight:500; color:#4b5563; }
        .moscow-item span { width:12px; height:12px; border-radius:3px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
