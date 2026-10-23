"""Protect model migration and production grounding defaults without contacting Google."""
import pytest

from atlas.config import Settings, settings
from atlas.agents.intake.agent import build_intake_agent
from atlas.agents.itinerary.agent import build_itinerary_agent
from atlas.agents.research.grounded import build_grounded_research_agent
from atlas.agents.research.structured import build_structured_research_agent


def test_production_defaults(monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("ITINERARY_MODEL", raising=False)
    monkeypatch.delenv("ENABLE_SEARCH_GROUNDING", raising=False)
    config = Settings(_env_file=None)
    assert config.default_model == "gemini-3.5-flash-lite"
    assert config.itinerary_model == "gemini-3.6-flash"
    assert config.enable_search_grounding is True


def test_environment_model_overrides_keep_hybrid_tiers_separate(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "gemini-test-replacement")
    monkeypatch.setenv("ITINERARY_MODEL", "gemini-test-writer")
    config = Settings(_env_file=None)
    monkeypatch.setattr(settings, "default_model", config.default_model)
    monkeypatch.setattr(settings, "itinerary_model", config.itinerary_model)
    for factory in (
        build_intake_agent,
        build_grounded_research_agent,
        build_structured_research_agent,
    ):
        assert factory().model.model == "gemini-test-replacement"
    assert build_itinerary_agent().model.model == "gemini-test-writer"


@pytest.mark.parametrize("enabled", [False, True])
def test_search_setting_controls_tools(monkeypatch, enabled):
    monkeypatch.setenv("ENABLE_SEARCH_GROUNDING", str(enabled))
    config = Settings(_env_file=None)
    monkeypatch.setattr(settings, "enable_search_grounding", config.enable_search_grounding)
    agent = build_grounded_research_agent()
    if enabled:
        assert [tool.name for tool in agent.tools] == ["google_search"]
        assert "Use Google Search" in agent.instruction
    else:
        assert agent.tools == []
        assert "no live" in agent.instruction
        assert "Do not claim" in agent.instruction
