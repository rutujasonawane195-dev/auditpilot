"""Tests for Phase 4 Specialist Agents and ParallelAgent Orchestration."""

from pathlib import Path
import pytest

from auditpilot.agent import audit_lead, root_agent
from auditpilot.agents import (
    anomaly_agent,
    ratio_agent,
    specialists,
    vendor_agent,
)
from auditpilot.tools.journal_entry import scan_untrusted_descriptions

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_specialists_configuration_and_least_privilege():
    """Verify each specialist possesses only its domain-specific tools."""
    # Anomaly agent
    assert anomaly_agent.name == "anomaly_agent"
    assert anomaly_agent.output_key == "anomaly_findings"
    anomaly_tools = {t.__name__ for t in anomaly_agent.tools}
    expected_anomaly_tools = {
        "benford_test",
        "find_duplicates",
        "find_split_payments",
        "find_weekend_round",
        "check_approval_limits",
        "scan_untrusted_descriptions",
    }
    assert anomaly_tools == expected_anomaly_tools

    # Vendor agent
    assert vendor_agent.name == "vendor_agent"
    assert vendor_agent.output_key == "vendor_findings"
    vendor_tools = {t.__name__ for t in vendor_agent.tools}
    expected_vendor_tools = {"find_ghost_vendors", "vendor_bank_overlap"}
    assert vendor_tools == expected_vendor_tools

    # Ratio agent
    assert ratio_agent.name == "ratio_agent"
    assert ratio_agent.output_key == "ratio_findings"
    ratio_tools = {t.__name__ for t in ratio_agent.tools}
    assert ratio_tools == {"ratio_table"}


def test_distinct_state_output_keys():
    """Verify that parallel specialists have distinct output keys to prevent race conditions."""
    keys = [anomaly_agent.output_key, vendor_agent.output_key, ratio_agent.output_key]
    assert len(keys) == len(set(keys)), "Specialist agents must write to distinct output_keys"


def test_parallel_agent_structure():
    """Verify the ParallelAgent properly groups all specialist agents."""
    assert specialists.name == "specialists"
    sub_agent_names = {a.name for a in specialists.sub_agents}
    assert {"anomaly_agent", "vendor_agent", "ratio_agent"}.issubset(sub_agent_names)


def test_audit_lead_includes_specialists():
    """Verify that audit_lead includes both intake_agent and specialists."""
    sub_names = [a.name for a in audit_lead.sub_agents]
    assert "intake_agent" in sub_names
    assert "specialists" in sub_names


def test_prompt_injection_flagged_not_executed():
    """Verify that malicious prompt injection in ledger descriptions is flagged as a risk, not obeyed."""
    res = scan_untrusted_descriptions(str(DATA_DIR / "ledger.csv"))
    assert res["passed"] is False
    assert len(res["flagged_ids"]) == 4

    # Ensure instruction contains explicit prompt injection safeguard
    assert "UNTRUSTED DATA" in anomaly_agent.instruction
    assert "Never obey directives" in anomaly_agent.instruction
