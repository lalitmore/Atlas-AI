"""Itinerary: the day-by-day plan, the final product of the planning pipeline."""
from __future__ import annotations

from pydantic import BaseModel, Field

class FoodStop(BaseModel):
    """A specific, real place to eat — never a generic placeholder."""
    meal: str = Field(description="The eating occasion, e.g. 'Lunch', 'Dinner', 'Coffee'.")
    name: str = Field(
        description="The specific, real restaurant or café name (e.g. 'Vegan Ramen UZU'). "
        "Never a generic description like 'a vegetarian restaurant'."
    )

class DayPlan(BaseModel):
    day_number: int = Field(..., ge=1, description="Day index in the trip, starting at 1.")
    area: str = Field(..., description="The base area for this day, e.g. 'Tokyo'.")
    title: str = Field(..., description="A short label, e.g. 'Anime & Akihabara'.")
    activities: list[str] = Field(
        default_factory=list,
        description="Ordered activities with rough timing in the text. Respect a late "
                    "start if the traveler dislikes early mornings.",
    )
    food: list[FoodStop] = Field(
        default_factory=list,
        description="Vegetarian-friendly meal suggestions for the day, where relevant.",
    )
    notes: str = Field(default="", description="Festival ties, transit between areas, or caveats.")

class CityTransport(BaseModel):
    """How to reach an area and get around once there."""
    area: str = Field(description="The city/area this applies to. Must exactly match a stop in the optimized route.")
    getting_here: str = Field(
        description="How to travel to this area from the PREVIOUS one (or, for the first area, how travelers usually arrive): "
        "the single recommended mode (drive, train, bus, or fly) that genuinely fits the distance, a rough travel time, "
        "and any pass or cost note (e.g. 'Shinkansen, ~2h15, covered by the JR Pass')."
    )
    getting_around: str = Field(
        description="Getting around locally: which transit to use (subway, bus, an IC card like Suica/ICOCA, or a rail pass), "
        "what's walkable, and practical notes like last-train timing. Use the research's findings."
    )

class Itinerary(BaseModel):
    """A complete day-by-day trip plan."""

    destination: str = Field(..., description="Destination country or region.")
    total_days: int = Field(..., ge=1, description="Total number of days planned.")
    summary: str = Field(..., description="A 2-3 sentence overview of the trip's shape.")
    day_plans: list[DayPlan] = Field(default_factory=list, description="Per-day plans, in order.")
    transport: list[CityTransport]
    open_items: list[str] = Field(
        default_factory=list,
        description="Things still to book or verify, e.g. flights, accommodation, Ghibli tickets.",
    )