"""DestinationResearch: the Research agent's structured proposal of where to go,
derived from a TripBrief. In Step 2 it comes from the model's own knowledge (no
live data); facts needing verification are flagged in `needs_grounding`."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateArea(BaseModel):
    name: str = Field(..., description="City or area name, e.g. 'Tokyo'.")
    region: str = Field(..., description="Broader region, e.g. 'Kanto'.")
    why_it_fits: str = Field(..., description="One or two sentences tying this area to the traveler's interests.")
    latitude: float = Field(..., description="Approximate latitude of the area's center.")
    longitude: float = Field(..., description="Approximate longitude of the area's center.")
    matched_interests: list[str] = Field(
        default_factory=list,
        description="Which of the traveler's interests this area serves, e.g. ['anime', 'nightlife'].",
    )


class DestinationResearch(BaseModel):
    """A first-pass, model-knowledge proposal of where a trip could go."""

    destination: str = Field(..., description="The destination country or region, echoed from the brief.")
    summary: str = Field(..., description="A short overview (2-3 sentences) tuned to this traveler's brief.")
    candidate_areas: list[CandidateArea] = Field(
        default_factory=list,
        description="Four to seven candidate cities or areas worth considering for this trip.",
    )
    seasonal_notes: str = Field(
        default="",
        description="What the chosen travel month typically means (weather, crowds, seasonal events).",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="The most important facts the grounded research confirmed, "
                    "e.g. a festival's real dates, a current price, a vegetarian-dining reality.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Anything inferred, plus a note that this pass is model knowledge, not live data.",
    )
    needs_grounding: list[str] = Field(
        default_factory=list,
        description=(
            "Specific facts to verify with live data before planning, e.g. "
            "'exact 2026 festival dates', 'current opening hours', 'real prices'."
        ),
    )
   