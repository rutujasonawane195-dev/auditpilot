"""Test Phase 0 setup and environment readiness."""
import importlib
import shutil
import subprocess
from pathlib import Path
import pytest


def test_core_dependencies():
    """Verify that all core libraries are installed and importable."""
    assert importlib.import_module("google.adk") is not None
    assert importlib.import_module("pandas") is not None
    assert importlib.import_module("pydantic") is not None
    assert importlib.import_module("pytest") is not None


def test_directory_structure():
    """Verify that the required repository directory structure exists."""
    repo_root = Path(__file__).resolve().parent.parent
    expected_dirs = [
        "auditpilot",
        "auditpilot/agents",
        "auditpilot/tools",
        "data",
        "scripts",
        "tests",
        "evals",
        "docs",
        ".agent/rules",
    ]
    is_container = not (repo_root / ".git").is_dir()
    for d in expected_dirs:
        if d == ".agent/rules" and is_container:
            # .agent is excluded by .dockerignore when packaged into container
            continue
        dir_path = repo_root / d
        assert dir_path.is_dir(), f"Expected directory {d} does not exist"


def test_agent_discovery():
    """Verify that auditpilot.agent exposes a root_agent."""
    from auditpilot.agent import root_agent

    assert root_agent is not None
    assert hasattr(root_agent, "name")
    assert root_agent.name in ["root_agent", "audit_lead"]


def test_gitignore_protects_env():
    """Verify that .env files are ignored by git."""
    repo_root = Path(__file__).resolve().parent.parent
    if shutil.which("git") is None or not (repo_root / ".git").is_dir():
        pytest.skip("Git repository not present (running inside production container)")

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    # Ensure no .env file is tracked or staged
    assert ".env" not in result.stdout
