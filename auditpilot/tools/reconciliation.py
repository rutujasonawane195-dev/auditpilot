"""Reconciliation and Ledger Integrity Tools."""

from pathlib import Path
from typing import Any, Dict, List
import pandas as pd


def load_ledger(filepath: str = "data/ledger.csv") -> Dict[str, Any]:
    """Load and profile journal entries ledger, validating data volume and columns.

    Args:
        filepath: Relative or absolute path to the ledger CSV file.

    Returns:
        Dict with test name, flagged_ids, descriptive stats, auditor notes, and passed boolean.
    """
    path = Path(filepath)
    if not path.exists():
        return {
            "test": "load_ledger",
            "flagged_ids": [],
            "stats": {"error": f"File not found: {filepath}"},
            "notes": "Failed: Ledger file missing.",
            "passed": False,
        }

    df = pd.read_csv(path)
    required_cols = [
        "entry_id", "date", "posted_by", "approved_by", "account_code",
        "account_name", "vendor_id", "amount_inr", "description"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]

    null_counts = int(df[required_cols].isnull().sum().sum()) if not missing_cols else int(df.isnull().sum().sum())
    total_spend = float(round(df["amount_inr"].sum(), 2)) if "amount_inr" in df.columns else 0.0

    stats = {
        "row_count": int(len(df)),
        "required_columns_present": len(missing_cols) == 0,
        "missing_columns": missing_cols,
        "total_null_fields": null_counts,
        "total_spend_inr": total_spend,
        "unique_vendors": int(df["vendor_id"].nunique()) if "vendor_id" in df.columns else 0,
        "unique_accounts": int(df["account_code"].nunique()) if "account_code" in df.columns else 0,
        "date_start": str(df["date"].min()) if "date" in df.columns else "",
        "date_end": str(df["date"].max()) if "date" in df.columns else "",
    }

    flagged_ids: List[str] = []
    if null_counts > 0:
        flagged_ids = df[df[required_cols].isnull().any(axis=1)]["entry_id"].astype(str).tolist()

    passed = (len(missing_cols) == 0) and (null_counts == 0)
    notes = (
        f"Loaded {len(df)} entries spanning {stats['date_start']} to {stats['date_end']}. "
        f"Total spend: INR {total_spend:,.2f}. Missing required columns: {missing_cols}."
    )

    return {
        "test": "load_ledger",
        "flagged_ids": flagged_ids,
        "stats": stats,
        "notes": notes,
        "passed": passed,
    }


def check_trial_balance(
    ledger_path: str = "data/ledger.csv",
    tb_path: str = "data/trial_balance.csv",
) -> Dict[str, Any]:
    """Verify trial balance equality (Debits == Credits) and tie ledger expenses.

    Args:
        ledger_path: Path to the general ledger CSV file.
        tb_path: Path to the trial balance CSV file.

    Returns:
        Dict with test name, flagged_ids, reconciliation stats, auditor notes, and passed boolean.
    """
    tb_file = Path(tb_path)
    if not tb_file.exists():
        return {
            "test": "check_trial_balance",
            "flagged_ids": ["TB_GAP_001"],
            "stats": {"error": f"Trial balance file not found: {tb_path}"},
            "notes": "Failed: Trial balance file missing.",
            "passed": False,
        }

    tb_df = pd.read_csv(tb_file)
    tot_debits = float(round(tb_df["debit"].sum(), 2))
    tot_credits = float(round(tb_df["credit"].sum(), 2))
    imbalance = float(round(abs(tot_debits - tot_credits), 2))
    is_balanced = imbalance == 0.0

    flagged_ids: List[str] = []
    if not is_balanced:
        flagged_ids.append("TB_GAP_001")

    # Tie expenses between ledger and trial balance
    ledger_file = Path(ledger_path)
    ledger_tied = True
    expense_gap = 0.0

    if ledger_file.exists():
        ledger_df = pd.read_csv(ledger_file)
        ledger_exp_sum = float(round(ledger_df["amount_inr"].sum(), 2))

        # Filter expense accounts in trial balance (codes starting with 5 or 6)
        tb_exp_mask = tb_df["account"].str.match(r"^[56]\d{3}")
        tb_exp_sum = float(round(tb_df.loc[tb_exp_mask, "debit"].sum(), 2))
        expense_gap = float(round(abs(ledger_exp_sum - tb_exp_sum), 2))
        ledger_tied = expense_gap == 0.0

    stats = {
        "total_debits": tot_debits,
        "total_credits": tot_credits,
        "imbalance": imbalance,
        "is_balanced": is_balanced,
        "ledger_tied": ledger_tied,
        "expense_reconciliation_gap": expense_gap,
    }

    notes = (
        f"Trial Balance reconciliation: Debits=INR {tot_debits:,.2f}, Credits=INR {tot_credits:,.2f}. "
        f"Imbalance=INR {imbalance:,.2f}. Balanced={is_balanced}."
    )

    return {
        "test": "check_trial_balance",
        "flagged_ids": flagged_ids,
        "stats": stats,
        "notes": notes,
        "passed": is_balanced and ledger_tied,
    }
