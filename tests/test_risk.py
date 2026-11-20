"""Tests for Phase 6 Finding Schema and Risk Scoring."""

import pytest
from pydantic import ValidationError

from auditpilot.agent import audit_lead
from auditpilot.agents.risk import risk_agent, score_and_rank_findings
from auditpilot.schemas import Finding, RankedFindings


def test_finding_score_calculation():
    """Verify that score is computed strictly by code as likelihood * impact."""
    f = Finding(
        id="FIND-001",
        title="Ghost Vendor Disbursements",
        entry_ids=["JE_GHOST_01", "JE_GHOST_02"],
        amount_at_risk_inr=500000.0,
        likelihood=5,
        impact=4,
    )
    assert f.score == 20
    assert f.severity == "CRITICAL"


def test_finding_rejects_empty_entry_ids():
    """Verify that findings without cited entry_ids fail validation."""
    with pytest.raises(ValidationError) as exc_info:
        Finding(
            id="FIND-002",
            title="Unsubstantiated Claim",
            entry_ids=[],  # Empty list violates hard rule
            likelihood=3,
            impact=3,
        )
    assert "at least one entry_id" in str(exc_info.value)


def test_score_and_rank_findings_ordering():
    """Verify score_and_rank_findings sorts findings descending by score."""
    f1 = Finding(id="F1", title="Low Risk Item", entry_ids=["JE001"], likelihood=1, impact=2, amount_at_risk_inr=1000.0)
    f2 = Finding(id="F2", title="Critical Fraud", entry_ids=["JE002"], likelihood=5, impact=5, amount_at_risk_inr=800000.0)
    f3 = Finding(id="F3", title="Medium Policy Breach", entry_ids=["JE003"], likelihood=3, impact=3, amount_at_risk_inr=50000.0)

    ranked: RankedFindings = score_and_rank_findings([f1, f2, f3])
    assert ranked.total_findings == 3
    assert ranked.findings[0].id == "F2"  # score 25
    assert ranked.findings[1].id == "F3"  # score 9
    assert ranked.findings[2].id == "F1"  # score 2
    assert ranked.highest_score == 25
    assert ranked.total_exposure_inr == 851000.0


def test_risk_agent_configuration():
    """Verify risk_agent ADK configuration and output key."""
    assert risk_agent.name == "risk_agent"
    assert risk_agent.model == "gemini-3.8-flash"
    assert risk_agent.output_key == "ranked_findings"
    assert "Likelihood" in risk_agent.instruction
    assert "Impact" in risk_agent.instruction


def test_audit_lead_includes_risk_agent():
    """Verify audit_lead includes risk_agent in sequential workflow."""
    sub_names = [a.name for a in audit_lead.sub_agents]
    assert "intake_agent" in sub_names
    assert "specialists" in sub_names
    assert "risk_agent" in sub_names
