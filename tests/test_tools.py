"""Tests for Phase 2 Deterministic Audit Tools."""

from pathlib import Path
import pandas as pd
import pytest

from auditpilot.schemas import AuditToolResult, Finding, FindingCategory, FindingSeverity
from auditpilot.tools import (
    benford_test,
    check_approval_limits,
    check_trial_balance,
    find_duplicates,
    find_ghost_vendors,
    find_split_payments,
    find_weekend_round,
    load_ledger,
    ratio_table,
    scan_untrusted_descriptions,
    vendor_bank_overlap,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_load_ledger_success():
    """Verify load_ledger loads baseline data and computes accurate statistics."""
    res = load_ledger(str(DATA_DIR / "ledger.csv"))
    assert res["test"] == "load_ledger"
    assert res["passed"] is True
    assert res["stats"]["row_count"] >= 5900
    assert res["stats"]["total_spend_inr"] > 0
    assert res["stats"]["required_columns_present"] is True
    assert res["stats"]["total_null_fields"] == 0
    assert len(res["flagged_ids"]) == 0


def test_load_ledger_missing_file():
    """Verify load_ledger graceful degradation on missing file."""
    res = load_ledger("data/non_existent.csv")
    assert res["passed"] is False
    assert "error" in res["stats"]


def test_check_trial_balance():
    """Verify detection of the planted trial balance Rs 50,000 gap."""
    res = check_trial_balance(
        ledger_path=str(DATA_DIR / "ledger.csv"),
        tb_path=str(DATA_DIR / "trial_balance.csv"),
    )
    assert res["test"] == "check_trial_balance"
    assert res["passed"] is False
    assert "TB_GAP_001" in res["flagged_ids"]
    assert res["stats"]["imbalance"] == 50000.0
    assert res["stats"]["is_balanced"] is False


def test_benford_test():
    """Verify Benford's law conformity analysis."""
    res = benford_test(str(DATA_DIR / "ledger.csv"))
    assert res["test"] == "benford_test"
    assert "mad" in res["stats"]
    assert res["stats"]["sample_size"] > 5000
    assert res["stats"]["mad"] < 0.015  # Normal baseline transactions conform
    assert res["passed"] is True


def test_find_duplicates():
    """Verify detection of duplicate payment entries."""
    res = find_duplicates(str(DATA_DIR / "ledger.csv"), window_days=7)
    assert res["test"] == "find_duplicates"
    assert res["passed"] is False

    gt = pd.read_csv(DATA_DIR / "ground_truth.csv")
    expected_dups = set(gt[gt["anomaly_type"] == "duplicate_payment"]["entry_id"])

    flagged_set = set(res["flagged_ids"])
    # All 10 planted duplicate vouchers must be detected
    assert expected_dups.issubset(flagged_set)
    assert res["stats"]["duplicate_pairs_count"] >= 5


def test_find_split_payments():
    """Verify detection of split payments under the Rs 50,000 threshold."""
    res = find_split_payments(
        str(DATA_DIR / "ledger.csv"),
        min_amt=45000.0,
        limit_amt=50000.0,
    )
    assert res["test"] == "find_split_payments"
    assert res["passed"] is False

    gt = pd.read_csv(DATA_DIR / "ground_truth.csv")
    expected_splits = set(gt[gt["anomaly_type"] == "split_payment"]["entry_id"])

    flagged_set = set(res["flagged_ids"])
    assert expected_splits.issubset(flagged_set)
    assert res["stats"]["split_group_count"] >= 6


def test_find_weekend_round():
    """Verify detection of round-denomination payments posted on Sundays."""
    res = find_weekend_round(str(DATA_DIR / "ledger.csv"))
    assert res["test"] == "find_weekend_round"
    assert res["passed"] is False

    gt = pd.read_csv(DATA_DIR / "ground_truth.csv")
    expected_sun = set(gt[gt["anomaly_type"] == "sunday_round_amount"]["entry_id"])

    flagged_set = set(res["flagged_ids"])
    assert expected_sun == flagged_set
    assert len(res["flagged_ids"]) == 12


def test_check_approval_limits():
    """Verify segregation of duties check for self-approved vouchers."""
    res = check_approval_limits(str(DATA_DIR / "ledger.csv"))
    assert res["test"] == "check_approval_limits"
    assert res["passed"] is False

    gt = pd.read_csv(DATA_DIR / "ground_truth.csv")
    expected_self = set(gt[gt["anomaly_type"] == "self_approval"]["entry_id"])

    flagged_set = set(res["flagged_ids"])
    assert expected_self == flagged_set
    assert len(res["flagged_ids"]) == 8


def test_find_ghost_vendors():
    """Verify detection of ghost vendors lacking GSTIN/PAN and associated disbursements."""
    res = find_ghost_vendors(
        ledger_path=str(DATA_DIR / "ledger.csv"),
        vendors_path=str(DATA_DIR / "vendors.csv"),
    )
    assert res["test"] == "find_ghost_vendors"
    assert res["passed"] is False

    gt = pd.read_csv(DATA_DIR / "ground_truth.csv")
    expected_ghost = set(gt[gt["anomaly_type"] == "ghost_vendor"]["entry_id"])

    flagged_set = set(res["flagged_ids"])
    assert expected_ghost == flagged_set
    assert res["stats"]["ghost_vendors_count"] == 5


def test_vendor_bank_overlap():
    """Verify detection of vendor-employee shared bank accounts (conflict of interest)."""
    res = vendor_bank_overlap(
        ledger_path=str(DATA_DIR / "ledger.csv"),
        vendors_path=str(DATA_DIR / "vendors.csv"),
        employees_path=str(DATA_DIR / "employees.csv"),
        conflict_poster_only=True,
    )
    assert res["test"] == "vendor_bank_overlap"
    assert res["passed"] is False
    assert res["stats"]["shared_bank_vendors_count"] == 3

    gt = pd.read_csv(DATA_DIR / "ground_truth.csv")
    expected_shared = set(gt[gt["anomaly_type"] == "shared_bank_account"]["entry_id"])
    flagged_set = set(res["flagged_ids"])
    assert expected_shared.issubset(flagged_set)


def test_scan_untrusted_descriptions():
    """Verify detection of prompt injection and system override attempts in ledger descriptions."""
    res = scan_untrusted_descriptions(str(DATA_DIR / "ledger.csv"))
    assert res["test"] == "scan_untrusted_descriptions"
    assert res["passed"] is False

    gt = pd.read_csv(DATA_DIR / "ground_truth.csv")
    expected_inj = set(gt[gt["anomaly_type"] == "prompt_injection"]["entry_id"])

    flagged_set = set(res["flagged_ids"])
    assert expected_inj == flagged_set
    assert len(res["flagged_ids"]) == 4


def test_ratio_table():
    """Verify financial ratio table computations."""
    res = ratio_table(str(DATA_DIR / "financials.csv"))
    assert res["test"] == "ratio_table"
    assert res["stats"]["months_analyzed"] == 12
    assert "average_current_ratio" in res["stats"]
    assert "average_gross_margin" in res["stats"]
    assert res["passed"] is True


def test_schemas_and_models():
    """Verify AuditPilot Pydantic schema validation."""
    finding = Finding(
        finding_id="FIND-001",
        title="Unauthorized Sunday Round Disbursement",
        category=FindingCategory.JOURNAL_ENTRY,
        severity=FindingSeverity.HIGH,
        description="High-value round-sum transactions posted outside business hours.",
        entry_ids=["JE_SUN_ROUND_01", "JE_SUN_ROUND_02"],
        amount_inr=150000.0,
    )
    assert finding.finding_id == "FIND-001"
    assert len(finding.entry_ids) == 2
    assert finding.severity == FindingSeverity.HIGH

    tool_res = AuditToolResult(
        test="check_trial_balance",
        flagged_ids=["TB_GAP_001"],
        stats={"imbalance": 50000.0},
        notes="Trial balance gap detected.",
        passed=False,
    )
    assert tool_res.test == "check_trial_balance"
    assert tool_res.passed is False
