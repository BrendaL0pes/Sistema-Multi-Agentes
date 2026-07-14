"""Helpers for LLM-backed agents."""

from __future__ import annotations

import json
import re
from time import sleep
from typing import Any, TypeVar

from pydantic import ValidationError

SchemaT = TypeVar("SchemaT")


class LlmResponseError(RuntimeError):
    """Raised when the model provider does not return the expected structure."""


def run_structured_agent(
    agent: Any,
    prompt: str,
    schema_type: type[SchemaT],
    agent_name: str,
    attempts: int = 3,
) -> SchemaT:
    """Run an agent with structured output and retry transient provider failures."""

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = agent.run(prompt, output_schema=schema_type)
            return parse_structured_response(response, schema_type, agent_name)
        except LlmResponseError as exc:
            last_error = exc
            if "falha de conexao" not in str(exc).lower():
                raise
        except Exception as exc:
            last_error = exc

        try:
            response = agent.run(_json_fallback_prompt(prompt, schema_type))
            return parse_structured_response(response, schema_type, agent_name)
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                raise LlmResponseError(
                    f"{agent_name}: falha ao obter resposta estruturada da Groq. "
                    "Verifique instabilidade da API, VPN, limite de uso ou tente "
                    "novamente em alguns instantes."
                ) from exc

        sleep(attempt)

    raise LlmResponseError(str(last_error))


def parse_structured_response(
    response: Any,
    schema_type: type[SchemaT],
    agent_name: str,
) -> SchemaT:
    """Parse an Agno response into a Pydantic schema with friendly errors."""

    content = response.content
    if isinstance(content, schema_type):
        return content
    if isinstance(content, dict):
        return schema_type.model_validate(content)

    text = _response_text(response).strip()
    if not text or text.lower() == "connection error.":
        raise LlmResponseError(
            f"{agent_name}: falha de conexao com a Groq. "
            "Verifique internet, VPN, limite da API e modelo configurado."
        )

    try:
        return parse_structured_text(text, schema_type, agent_name)
    except ValidationError as exc:
        raise LlmResponseError(
            f"{agent_name}: a LLM nao retornou JSON estruturado valido. "
            f"Resposta recebida: {_preview(text)}"
        ) from exc


def parse_structured_text(
    text: str,
    schema_type: type[SchemaT],
    agent_name: str,
) -> SchemaT:
    """Parse raw LLM text into the expected schema."""

    cleaned = text.strip()
    if not cleaned or cleaned.lower() == "connection error.":
        raise LlmResponseError(
            f"{agent_name}: a Groq nao retornou conteudo valido."
        )
    try:
        return schema_type.model_validate_json(_extract_json(cleaned))
    except ValidationError as exc:
        raise LlmResponseError(
            f"{agent_name}: a LLM nao retornou JSON estruturado valido. "
            f"Resposta recebida: {_preview(cleaned)}"
        ) from exc


def _response_text(response: Any) -> str:
    if hasattr(response, "get_content_as_string"):
        return response.get_content_as_string()
    return str(response.content)


def _preview(text: str, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _json_fallback_prompt(prompt: str, schema_type: type[SchemaT]) -> str:
    schema = json.dumps(schema_type.model_json_schema(), ensure_ascii=True)
    return (
        f"{prompt}\n\n"
        "Retorne exclusivamente um JSON valido, sem markdown, sem comentario "
        "e sem texto antes ou depois. O JSON deve seguir este schema:\n"
        f"{schema}"
    )


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped

    start_positions = [
        position
        for position in (stripped.find("{"), stripped.find("["))
        if position != -1
    ]
    if not start_positions:
        return stripped

    start = min(start_positions)
    end = max(stripped.rfind("}"), stripped.rfind("]"))
    if end <= start:
        return stripped
    return stripped[start : end + 1]
