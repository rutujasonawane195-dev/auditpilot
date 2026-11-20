"""Tests for Phase 8 Audit Memo Reporting and Human Sign-Off Gate."""

import re
from pathlib import Path
import pytest

from auditpilot.agent import audit_lead, root_agent
from auditpilot.agents.report import report_agent
from auditpilot.schemas import Finding
from auditpilot.tools.reporting import approve_audit_memo, generate_audit_memo

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def sample_findings():
    """Create representative confirmed and dropped findings for report testing."""
    confirmed = [
        Finding(
            id="FIND-001",
            title="Split Invoices Under Threshold",
            entry_ids=["JE_SPLIT_001", "JE_SPLIT_002", "JE_SPLIT_003"],
            amount_at_risk_inr=147600.0,
            likelihood=5,
            impact=4,
            category="journal_entry",
            rationale="Repeated invoices to single vendor under Rs 50,000 approval limit.",
            recommendation="Enforce system-wide PO aggregation controls.",
        ),
        Finding(
            id="FIND-002",
            title="Sunday Round Amount Disbursement",
            entry_ids=["JE_SUN_ROUND_01"],
            amount_at_risk_inr=100000.0,
            likelihood=4,
            impact=4,
            category="journal_entry",
            rationale="Weekend emergency posting without dual sign-off.",
        ),
    ]
    dropped = [
        Finding(
            id="FIND-FAKE-003",
            title="Hallucinated Duplicate Payment",
            entry_ids=["JE_FAKE_99999"],
            amount_at_risk_inr=500000.0,
            likelihood=3,
            impact=3,
            status="dropped",
            dropped_reason="Cited entry ID JE_FAKE_99999 not present in general ledger.",
        )
    ]
    return confirmed, dropped


def test_generate_audit_memo_draft(tmp_path: Path, sample_findings):
    """Verify memo is created with DRAFT status and includes all 6 sections."""
    confirmed, dropped = sample_findings
    memo_file = tmp_path / "audit_memo.md"

    res = generate_audit_memo(
        confirmed_findings=confirmed,
        dropped_findings=dropped,
        memo_path=str(memo_file),
        status="DRAFT",
    )
    assert res["test"] == "generate_audit_memo"
    assert memo_file.exists()

    content = memo_file.read_text(encoding="utf-8")
    # Verify DRAFT status
    assert "DRAFT - PENDING PARTNER APPROVAL" in content
    assert "FINAL" not in content

    # Verify all 6 mandatory sections exist
    expected_sections = [
        "## 1. Scope and Population Data",
        "## 2. Executive Summary",
        "## 3. Ranked Audit Findings",
        "## 4. Recommended Management Actions",
        "## 5. Scope Limitations",
        "## 6. Appendix: Dropped Findings",
    ]
    for section in expected_sections:
        assert section in content, f"Missing section: {section}"

    # Verify cited entry IDs appear in findings
    assert "JE_SPLIT_001" in content
    assert "JE_SUN_ROUND_01" in content

    # Verify dropped finding appears in appendix with reason
    assert "FIND-FAKE-003" in content
    assert "JE_FAKE_99999 not present in general ledger" in content


def test_approve_audit_memo_flips_to_final(tmp_path: Path, sample_findings):
    """Verify calling approve_audit_memo transitions status from DRAFT to FINAL."""
    confirmed, dropped = sample_findings
    memo_file = tmp_path / "audit_memo.md"

    # 1. Generate DRAFT
    generate_audit_memo(confirmed, dropped, memo_path=str(memo_file), status="DRAFT")

    # 2. Human Partner Signs Off
    approval_res = approve_audit_memo(
        memo_path=str(memo_file),
        reviewer="Managing Partner Sarah Jenkins, FCA",
        decision="approve",
        reviewer_notes="Evidence checked against ledger and bank master. Approved for release.",
    )
    assert approval_res["test"] == "approve_audit_memo"
    assert approval_res["stats"]["status"] == "FINAL"

    content = memo_file.read_text(encoding="utf-8")
    # Must now be stamped FINAL
    assert "FINAL - APPROVED" in content
    assert "DRAFT" not in content
    assert "Sarah Jenkins, FCA" in content
    assert "Human Partner Sign-Off & Approval Block" in content


def test_zero_number_drift_validation(tmp_path: Path, sample_findings):
    """Verify that financial numbers in the memo exactly match tool calculations."""
    confirmed, dropped = sample_findings
    memo_file = tmp_path / "audit_memo.md"

    generate_audit_memo(
        confirmed_findings=confirmed,
        dropped_findings=dropped,
        memo_path=str(memo_file),
    )
    content = memo_file.read_text(encoding="utf-8")

    # Expected numbers from tool calculations
    expected_total_exposure = sum(f.amount_at_risk_inr for f in confirmed)
    assert f"INR {expected_total_exposure:,.2f}" in content
    assert f"INR {confirmed[0].amount_at_risk_inr:,.2f}" in content
    assert f"INR {confirmed[1].amount_at_risk_inr:,.2f}" in content


def test_full_pipeline_orchestration():
    """Verify audit_lead wires the complete 5-stage sequential workflow."""
    sub_names = [a.name for a in root_agent.sub_agents]
    expected_pipeline = [
        "intake_agent",
        "specialists",
        "risk_agent",
        "skeptic_loop",
        "report_agent",
    ]
    assert sub_names == expected_pipeline

    assert report_agent.name == "report_agent"
    assert report_agent.output_key == "audit_memo_status"
    tool_names = {t.__name__ for t in report_agent.tools}
    assert tool_names == {"generate_audit_memo", "approve_audit_memo"}
