"""The TripBrief: the typed contract produced by the Intake agent and consumed
by every downstream agent in the Atlas pipeline."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class BudgetBasis(str, Enum):
    TOTAL = "total"
    PER_PERSON = "per_person"
    PER_DAY = "per_day"


class Budget(BaseModel):
    amount: float = Field(..., description="The numeric budget amount.")
    currency: str = Field(default="USD", description="ISO 4217 code, e.g. USD, EUR, JPY.")
    basis: BudgetBasis = Field(
        default=BudgetBasis.TOTAL,
        description="Whether the amount is a total, per person, or per day.",
    )


class TravelWindow(BaseModel):
    month: str | None = Field(default=None, description="Target month if given, e.g. 'October'.")
    start_date: date | None = Field(default=None, description="Exact start date if stated, else null.")
    end_date: date | None = Field(default=None, description="Exact end date if stated, else null.")
    flexible: bool = Field(default=False, description="True if the user said dates are flexible.")


class Constraints(BaseModel):
    avoid_early_mornings: bool = Field(
        default=False, description="True if the user dislikes early starts."
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="Dietary needs across the party, e.g. ['vegetarian'].",
    )
    max_walking_per_day_km: float | None = Field(
        default=None, description="Walking tolerance per day in km, if stated."
    )
    other: list[str] = Field(
        default_factory=list,
        description="Any other constraints stated, in the user's own words.",
    )


class TripBrief(BaseModel):
    """A structured, validated summary of a traveler's request."""

    destination: str = Field(..., description="Primary destination country or region, e.g. 'Japan'.")
    duration_days: int = Field(..., ge=1, description="Trip length in days. At least 1.")
    travel_window: TravelWindow = Field(
        default_factory=TravelWindow, description="When the trip should happen."
    )
    party_size: int = Field(default=1, ge=1, description="Number of travelers.")
    budget: Budget | None = Field(default=None, description="Budget, if the user provided one.")
    interests: list[str] = Field(
        default_factory=list,
        description="Short lowercase interest tags, e.g. ['anime', 'food', 'nature'].",
    )
    constraints: Constraints = Field(
        default_factory=Constraints, description="Scheduling, dietary, and other constraints."
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description=(
            "Anything you inferred that was not explicitly stated, in plain language. "
            "Example: 'Assumed 2 travelers from mention of a girlfriend.' Be honest; "
            "do not invent facts."
        ),
    )
    missing_info: list[str] = Field(
        default_factory=list,
        description=(
            "Important details a planner would need but the user did not provide, "
            "e.g. 'departure city'. Empty if nothing is missing."
        ),
    )