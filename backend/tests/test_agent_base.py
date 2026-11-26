"""
Unit Tests for Agent Foundation & Base Architecture
"""

import pytest
from app.agents.base import BaseAgent
from app.agents.schemas import AgentRecommendationCandidate


class DummyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="DummyAgent", element_role="Test Element")

    def run(self, context, **kwargs):
        self.log_execution("dummy_action", {"key": "val"})
        return "dummy_result"


def test_base_agent_initialization():
    agent = DummyAgent()
    assert agent.name == "DummyAgent"
    assert agent.element_role == "Test Element"
    result = agent.run({})
    assert result == "dummy_result"


def test_agent_recommendation_schema_validation():
    candidate = AgentRecommendationCandidate(
        subject_id="subj-1",
        topic_id="top-1",
        agent_element="Performance Element",
        type="retention_decay",
        priority="high",
        title="Review Logic Gates",
        reason_type="decay_risk",
        reason_detail="Memory retention is 45%",
        suggested_slot="Evening",
        estimated_duration_minutes=45,
    )
    assert candidate.agent_element == "Performance Element"
    assert candidate.priority == "high"
    assert candidate.estimated_duration_minutes == 45
