"""Tests for Phase 1 Synthetic Data Generation."""

from pathlib import Path
import hashlib
import pandas as pd
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_required_files_exist():
    """Verify all 7 required files are present in data/."""
    expected_files = [
        "ledger.csv",
        "vendors.csv",
        "employees.csv",
        "trial_balance.csv",
        "financials.csv",
        "policy.md",
        "ground_truth.csv",
    ]
    for filename in expected_files:
        file_path = DATA_DIR / filename
        assert file_path.exists(), f"Missing file: {filename}"
        assert file_path.stat().st_size > 0, f"File is empty: {filename}"


def test_ground_truth_counts():
    """Verify exact counts of planted anomalies in ground_truth.csv."""
    gt_file = DATA_DIR / "ground_truth.csv"
    assert gt_file.exists(), "ground_truth.csv not found"

    df = pd.read_csv(gt_file)
    counts = df["anomaly_type"].value_counts().to_dict()

    expected_counts = {
        "duplicate_payment": 10,
        "split_payment": 18,
        "ghost_vendor": 5,
        "shared_bank_account": 3,
        "self_approval": 8,
        "sunday_round_amount": 12,
        "trial_balance_gap": 1,
        "prompt_injection": 4,
    }

    assert counts == expected_counts, f"Mismatch in planted anomalies: {counts} vs {expected_counts}"
    assert len(df) == 61, f"Expected 61 total ground truth entries, found {len(df)}"


def test_ledger_schema_and_volume():
    """Verify ledger schema and row count constraints."""
    ledger_path = DATA_DIR / "ledger.csv"
    df = pd.read_csv(ledger_path)

    expected_cols = {
        "entry_id", "date", "posted_by", "approved_by", "account_code",
        "account_name", "vendor_id", "amount_inr", "description"
    }
    assert expected_cols.issubset(set(df.columns))

    # Around 6,000 rows
    assert 5900 <= len(df) <= 6100, f"Ledger row count out of range: {len(df)}"

    # Date range spans FY 2025-26
    df["date"] = pd.to_datetime(df["date"])
    assert df["date"].min() >= pd.Timestamp("2025-04-01")
    assert df["date"].max() <= pd.Timestamp("2026-03-31")


def test_trial_balance_gap():
    """Verify the trial balance has an intentional Rs 50,000 gap."""
    tb_path = DATA_DIR / "trial_balance.csv"
    df = pd.read_csv(tb_path)

    tot_debits = df["debit"].sum()
    tot_credits = df["credit"].sum()
    gap = round(tot_debits - tot_credits, 2)

    assert gap == 50000.0, f"Expected trial balance gap of 50,000 INR, got {gap}"


def test_deterministic_reproducibility():
    """Verify that re-running make_data produces identical hashes."""
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parent.parent
    python_bin = sys.executable

    def hash_file(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before_hashes = {f.name: hash_file(f) for f in DATA_DIR.glob("*") if f.is_file()}

    # Re-run make_data
    result = subprocess.run(
        [python_bin, str(repo_root / "scripts" / "make_data.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0

    after_hashes = {f.name: hash_file(f) for f in DATA_DIR.glob("*") if f.is_file()}
    assert before_hashes == after_hashes, "Data files are not deterministic across runs!"
