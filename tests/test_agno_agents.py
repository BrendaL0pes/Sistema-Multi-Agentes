"""Smoke tests for Agno agent factories."""

from agno.agent import Agent

from req_multiagent.analysis.ambiguity_agent import create_ambiguity_agent
from req_multiagent.analysis.conflict_agent import create_conflict_agent
from req_multiagent.analysis.gap_agent import create_gap_agent
from req_multiagent.analysis.prioritization_agent import create_prioritization_agent
from req_multiagent.ingestion.extractor_agent import create_extractor_agent
from req_multiagent.orchestration.consolidator_agent import create_consolidator_agent
from req_multiagent.orchestration.project_update_agent import (
    create_adjustment_agent,
    create_chat_agent,
    create_project_update_agent,
)


def test_agent_factories_return_agno_agents() -> None:
    factories = (
        (create_extractor_agent, "Requirements Extractor"),
        (create_ambiguity_agent, "Ambiguity Analyst"),
        (create_conflict_agent, "Conflict Analyst"),
        (create_prioritization_agent, "Prioritization Analyst"),
        (create_gap_agent, "Gap Analyst"),
        (create_consolidator_agent, "Requirements Consolidator"),
        (create_project_update_agent, "Project Update Agent"),
        (create_adjustment_agent, "Requirements Adjustment Agent"),
        (create_chat_agent, "Requirements Chat Agent"),
    )

    for factory, expected_name in factories:
        agent = factory()
        assert isinstance(agent, Agent)
        assert agent.name == expected_name
