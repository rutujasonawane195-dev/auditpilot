"""Tests for Phase 7 Skeptic Agent, Evidence Verification, and Skeptic Loop."""

from pathlib import Path
import pytest

from auditpilot.agent import audit_lead
from auditpilot.agents.skeptic import (
    review_and_filter_findings,
    skeptic_agent,
    skeptic_loop,
)
from auditpilot.schemas import Finding
from auditpilot.tools.verification import verify_entry_ids

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LEDGER_FILE = str(DATA_DIR / "ledger.csv")


def test_verify_entry_ids_tool():
    """Verify verify_entry_ids identifies existing vs missing entry IDs."""
    # Seeded real entries from Phase 1
    real_ids = ["JE000001", "JE_SUN_ROUND_01", "TB_GAP_001"]
    res_real = verify_entry_ids(real_ids, ledger_path=LEDGER_FILE)
    assert res_real["test"] == "verify_entry_ids"
    assert res_real["stats"]["all_valid"] is True
    assert len(res_real["stats"]["missing_ids"]) == 0
    assert len(res_real["flagged_ids"]) == 0

    # Fabricated / hallucinated entry IDs
    fake_ids = ["JE_FAKE_99999", "JE_HALLUCINATION_404"]
    res_fake = verify_entry_ids(fake_ids, ledger_path=LEDGER_FILE)
    assert res_fake["stats"]["all_valid"] is False
    assert set(res_fake["flagged_ids"]) == set(fake_ids)
    assert res_fake["stats"]["missing_count"] == 2


def test_skeptic_loop_drops_fake_finding():
    """Verify that a fake finding with non-existent entry IDs is dropped, not confirmed."""
    real_finding = Finding(
        id="FIND-REAL-001",
        title="Valid Sunday Round Amount",
        entry_ids=["JE_SUN_ROUND_01"],
        amount_at_risk_inr=100000.0,
        likelihood=4,
        impact=4,
    )
    fake_finding = Finding(
        id="FIND-FAKE-002",
        title="Fabricated Fraud Claim",
        entry_ids=["JE_FAKE_99999"],  # Does not exist in ledger
        amount_at_risk_inr=999999.0,
        likelihood=5,
        impact=5,
    )

    confirmed, dropped = review_and_filter_findings(
        [real_finding, fake_finding],
        ledger_path=LEDGER_FILE,
    )

    # Real finding must be confirmed
    assert len(confirmed) == 1
    assert confirmed[0].id == "FIND-REAL-001"
    assert confirmed[0].status == "confirmed"

    # Fake finding must be dropped with explicit reason, not silently lost
    assert len(dropped) == 1
    assert dropped[0].id == "FIND-FAKE-002"
    assert dropped[0].status == "dropped"
    assert "JE_FAKE_99999" in dropped[0].dropped_reason


def test_skeptic_agent_and_loop_configuration():
    """Verify skeptic_agent and skeptic_loop ADK configurations."""
    assert skeptic_agent.name == "skeptic_agent"
    assert skeptic_agent.model == "gemini-3.8-flash"
    assert skeptic_agent.output_key == "confirmed_findings"
    assert "verify_entry_ids" in [t.__name__ for t in skeptic_agent.tools]

    # Verify LoopAgent properties
    assert skeptic_loop.name == "skeptic_loop"
    assert skeptic_loop.max_iterations == 3
    assert skeptic_loop.sub_agents[0].name == "skeptic_agent"


def test_audit_lead_includes_skeptic_loop():
    """Verify audit_lead includes skeptic_loop in workflow."""
    sub_names = [a.name for a in audit_lead.sub_agents]
    assert "intake_agent" in sub_names
    assert "specialists" in sub_names
    assert "risk_agent" in sub_names
    assert "skeptic_loop" in sub_names
