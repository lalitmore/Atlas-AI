# Atlas API container for Cloud Run.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Install the package + its dependencies from pyproject.
COPY pyproject.toml ./
COPY atlas ./atlas
RUN pip install .

# Run as a non-root user.
RUN adduser --disabled-password --no-create-home appuser
USER appuser

# Cloud Run provides $PORT (8080). Shell form so the variable expands.
CMD ["sh", "-c", "uvicorn atlas.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]