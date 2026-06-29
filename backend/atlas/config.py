"""Central application configuration.

Loaded from environment variables. Our own code (the FastAPI service we add later)
imports `settings` from here, so configuration lives in exactly one place.

Note: the ADK dev tools (`adk web`, `adk run`) load the .env inside the agent folder
themselves and the genai SDK reads GOOGLE_API_KEY directly from the environment.
This module's job in Step 1 is to own the model name.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str = ""
    google_genai_use_vertexai: bool = False

    # The Gemini model Atlas uses by default. Centralised so a model migration
    # (e.g. when gemini-2.5-flash is retired on 2026-10-16) is a one-line change.
    
    #default_model: str = "gemini-2.5-flash"
    default_model: str = "gemini-2.5-flash-lite"


settings = Settings()