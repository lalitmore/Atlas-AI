"""Gemini settings shared by uvicorn and ADK entry points."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PIPELINE_ENV_FILE = Path(__file__).resolve().parent / "agents" / "pipeline" / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PIPELINE_ENV_FILE, extra="ignore")

    google_api_key: str = ""
    google_genai_use_vertexai: bool = False
    google_cloud_project: str = ""
    google_cloud_location: str = ""
    default_model: str = "gemini-3.5-flash-lite"
    itinerary_model: str = "gemini-3.6-flash"
    # Production uses live Google Search with the configured Tier 1 billing account.
    # Set false explicitly only for offline fixtures or general-knowledge drafts.
    enable_search_grounding: bool = True

    @field_validator("google_genai_use_vertexai", mode="before")
    @classmethod
    def normalize_vertex_mode(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @property
    def gemini_host(self) -> str:
        override = os.environ.get(
            "GOOGLE_VERTEX_BASE_URL" if self.google_genai_use_vertexai else "GOOGLE_GEMINI_BASE_URL"
        )
        if override:
            return urlsplit(override).hostname or "invalid-endpoint-host"
        if not self.google_genai_use_vertexai:
            return "generativelanguage.googleapis.com"
        if self.google_cloud_location in {"us", "eu"}:
            return f"aiplatform.{self.google_cloud_location}.rep.googleapis.com"
        if self.google_cloud_location == "global":
            return "aiplatform.googleapis.com"
        return f"{self.google_cloud_location}-aiplatform.googleapis.com"


settings = Settings()


def validate_runtime_config(config: Settings = settings) -> None:
    """Fail before serving requests; never print credentials or enable a paid backend."""
    if not config.google_genai_use_vertexai and not config.google_api_key.strip():
        raise RuntimeError(
            "GOOGLE_API_KEY is missing. Set it in the environment or "
            "backend/atlas/agents/pipeline/.env before starting Atlas."
        )
    if config.google_genai_use_vertexai:
        if not config.google_cloud_project or not re.fullmatch(
            r"[a-z][a-z0-9-]*", config.google_cloud_location
        ):
            raise RuntimeError(
                "Vertex mode requires GOOGLE_CLOUD_PROJECT and a valid GOOGLE_CLOUD_LOCATION. "
                "Set GOOGLE_GENAI_USE_VERTEXAI=false to use the Gemini Developer API."
            )
    base_var = "GOOGLE_VERTEX_BASE_URL" if config.google_genai_use_vertexai else "GOOGLE_GEMINI_BASE_URL"
    if os.environ.get(base_var):
        try:
            url = urlsplit(os.environ[base_var])
            valid = url.scheme in {"http", "https"} and url.hostname and (url.port is None or url.port > 0)
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError(f"{base_var} must be an absolute HTTP(S) URL with a valid hostname.")
    enterprise = os.environ.get("GOOGLE_GENAI_USE_ENTERPRISE")
    if enterprise is not None:
        normalized = enterprise.strip().lower()
        if normalized not in {"true", "false", "1", "0"} or (
            normalized in {"true", "1"}
        ) != config.google_genai_use_vertexai:
            raise RuntimeError(
                "GOOGLE_GENAI_USE_ENTERPRISE conflicts with GOOGLE_GENAI_USE_VERTEXAI. "
                "Remove the conflicting override before starting Atlas."
            )
        os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = str(config.google_genai_use_vertexai).lower()
    # genai reads os.environ itself. Give it the same normalized mode that we validated.
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = str(config.google_genai_use_vertexai).lower()
    if config.google_api_key:
        os.environ["GOOGLE_API_KEY"] = config.google_api_key.strip()
    backend = "Vertex" if config.google_genai_use_vertexai else "Developer API"
    logging.getLogger("uvicorn.error").info(
        "Gemini backend=%s host=%s model=%s api_key_configured=%s",
        backend, config.gemini_host, config.default_model, bool(config.google_api_key.strip()),
    )
