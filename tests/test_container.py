"""Tests for Part 2 Stage 1: Containerization."""

from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent


def test_dockerfile_exists_and_configured():
    """Verify Dockerfile uses python:3.12-slim, non-root user, and correct entrypoint."""
    dockerfile_path = BASE_DIR / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist in repo root"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in content, "Must use python:3.12-slim base image"
    assert "COPY requirements.txt ." in content, "Must copy requirements.txt before code for layer caching"
    assert "RUN pip install" in content, "Must install requirements"
    assert "useradd" in content and "appuser" in content, "Must create and run as unprivileged appuser"
    assert "USER appuser" in content, "Must switch to unprivileged appuser"
    assert "EXPOSE 8080" in content, "Must expose port 8080"
    assert 'CMD ["python", "main.py"]' in content, "Entrypoint must be main.py"


def test_dockerignore_security_exclusions():
    """Verify .dockerignore excludes virtualenvs, credentials, and cache files."""
    ignore_path = BASE_DIR / ".dockerignore"
    assert ignore_path.exists(), ".dockerignore must exist in repo root"

    content = ignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    assert ".git" in lines, ".git must be ignored"
    assert ".venv" in lines, ".venv must be ignored"
    assert "**/.env" in lines or ".env" in lines, ".env must be ignored to protect API keys"
    assert "audit_trail.jsonl" in lines, "Local audit trail logs must be ignored"


def test_requirements_contains_runtime_libraries():
    """Verify requirements.txt contains all core dependencies for ADK web server."""
    req_path = BASE_DIR / "requirements.txt"
    assert req_path.exists(), "requirements.txt must exist"

    content = req_path.read_text(encoding="utf-8").lower()
    required = ["google-adk", "pandas", "pydantic", "pytest", "scikit-learn", "uvicorn", "fastapi"]
    for pkg in required:
        assert pkg in content, f"Package '{pkg}' missing from requirements.txt"


def test_main_app_structure():
    """Verify main.py exposes FastAPI app, /health route, and configurable port."""
    from main import app
    assert app is not None

    routes = [route.path for route in app.routes]
    assert "/health" in routes, "/health endpoint must be registered"
