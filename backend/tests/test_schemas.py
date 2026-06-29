"""Schema contract tests — fast, no model calls."""
import pytest
from pydantic import ValidationError

from atlas.schemas import TripBrief, DestinationResearch


def test_trip_brief_parses_minimal():
    brief = TripBrief.model_validate({"destination": "Japan", "duration_days": 10})
    assert brief.destination == "Japan"
    assert brief.party_size == 1      # default applied
    assert brief.budget is None       # optional, not provided


def test_trip_brief_rejects_zero_days():
    with pytest.raises(ValidationError):
        TripBrief.model_validate({"destination": "Japan", "duration_days": 0})


def test_destination_research_parses():
    research = DestinationResearch.model_validate({
        "destination": "Japan",
        "summary": "A mix of city energy and nature.",
        "candidate_areas": [{
            "name": "Tokyo", "region": "Kanto",
            "latitude": 35.68, "longitude": 139.69,
            "why_it_fits": "Anime hubs and dense nightlife.",
            "matched_interests": ["anime", "nightlife"],
        }],
    })
    assert research.candidate_areas[0].name == "Tokyo"