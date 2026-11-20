"""Test Phase 0 setup and environment readiness."""
import importlib
import subprocess
from pathlib import Path


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
    for d in expected_dirs:
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
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    # Ensure no .env file is tracked or staged
    assert ".env" not in result.stdout
