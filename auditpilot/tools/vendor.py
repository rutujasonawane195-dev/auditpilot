"""Vendor Audit and KYC Verification Tools."""

from pathlib import Path
from typing import Any, Dict, List
import pandas as pd


def find_ghost_vendors(
    ledger_path: str = "data/ledger.csv",
    vendors_path: str = "data/vendors.csv",
) -> Dict[str, Any]:
    """Identify ghost vendors (missing GSTIN or PAN) and associated payments.

    Args:
        ledger_path: Path to ledger CSV file.
        vendors_path: Path to vendors CSV file.

    Returns:
        Dict with test name, flagged_ids (payment vouchers to ghost vendors), stats, and notes.
    """
    v_path = Path(vendors_path)
    l_path = Path(ledger_path)

    if not v_path.exists() or not l_path.exists():
        return {
            "test": "find_ghost_vendors",
            "flagged_ids": [],
            "stats": {"error": "Missing vendor or ledger dataset."},
            "notes": "Failed: Master vendor or ledger file missing.",
            "passed": False,
        }

    vendors_df = pd.read_csv(v_path)
    ledger_df = pd.read_csv(l_path)

    # Missing GSTIN or PAN indicates incomplete KYC / ghost shell company
    gstin_missing = vendors_df["gstin"].isna() | (vendors_df["gstin"].astype(str).str.strip() == "")
    pan_missing = vendors_df["pan"].isna() | (vendors_df["pan"].astype(str).str.strip() == "")
    ghost_vendors_df = vendors_df[gstin_missing | pan_missing]
    ghost_vendor_ids = ghost_vendors_df["vendor_id"].tolist()

    ghost_payments = ledger_df[ledger_df["vendor_id"].isin(ghost_vendor_ids)]
    flagged_ids = sorted(ghost_payments["entry_id"].astype(str).tolist())
    total_amount = float(round(ghost_payments["amount_inr"].sum(), 2))

    stats = {
        "ghost_vendor_ids": ghost_vendor_ids,
        "ghost_vendors_count": len(ghost_vendor_ids),
        "ghost_payments_count": len(flagged_ids),
        "total_ghost_disbursements_inr": total_amount,
    }

    notes = (
        f"Detected {len(ghost_vendor_ids)} unverified ghost vendors lacking mandatory GSTIN/PAN "
        f"with {len(flagged_ids)} disbursement transactions totaling INR {total_amount:,.2f}."
    )

    return {
        "test": "find_ghost_vendors",
        "flagged_ids": flagged_ids,
        "stats": stats,
        "notes": notes,
        "passed": len(flagged_ids) == 0,
    }


def vendor_bank_overlap(
    ledger_path: str = "data/ledger.csv",
    vendors_path: str = "data/vendors.csv",
    employees_path: str = "data/employees.csv",
    conflict_poster_only: bool = False,
) -> Dict[str, Any]:
    """Identify vendor-employee shared bank accounts (Conflict of Interest).

    Args:
        ledger_path: Path to ledger CSV file.
        vendors_path: Path to vendors CSV file.
        employees_path: Path to employees CSV file.
        conflict_poster_only: If True, only flags entries posted directly by the conflicting employee.
                             If False, flags all transactions involving the conflicting vendors.

    Returns:
        Dict with test name, flagged_ids, conflict stats, and notes.
    """
    v_path = Path(vendors_path)
    e_path = Path(employees_path)
    l_path = Path(ledger_path)

    if not v_path.exists() or not e_path.exists() or not l_path.exists():
        return {
            "test": "vendor_bank_overlap",
            "flagged_ids": [],
            "stats": {"error": "Missing vendor, employee, or ledger dataset."},
            "notes": "Failed: Master vendor, employee, or ledger dataset missing.",
            "passed": False,
        }

    vendors_df = pd.read_csv(v_path)
    employees_df = pd.read_csv(e_path)
    ledger_df = pd.read_csv(l_path)

    # Match bank accounts between employees and vendors
    vendors_df["bank_account_clean"] = vendors_df["bank_account"].astype(str).str.strip()
    employees_df["bank_account_clean"] = employees_df["bank_account"].astype(str).str.strip()

    emp_account_map = dict(zip(employees_df["bank_account_clean"], employees_df["emp_id"]))
    shared_vendors_df = vendors_df[vendors_df["bank_account_clean"].isin(emp_account_map.keys())]
    shared_vendor_ids = shared_vendors_df["vendor_id"].tolist()

    conflict_details: List[Dict[str, Any]] = []
    conflict_posted_eids: List[str] = []

    for _, row in shared_vendors_df.iterrows():
        v_id = row["vendor_id"]
        v_name = row["name"]
        bank_acc = row["bank_account_clean"]
        matching_emp_id = emp_account_map[bank_acc]
        matching_emp_row = employees_df[employees_df["emp_id"] == matching_emp_id].iloc[0]

        # Find transactions to this vendor posted by the matching employee
        emp_posted_tx = ledger_df[(ledger_df["vendor_id"] == v_id) & (ledger_df["posted_by"] == matching_emp_id)]
        posted_eids = emp_posted_tx["entry_id"].astype(str).tolist()
        conflict_posted_eids.extend(posted_eids)

        conflict_details.append({
            "vendor_id": v_id,
            "vendor_name": v_name,
            "bank_account": bank_acc,
            "employee_id": matching_emp_id,
            "employee_name": matching_emp_row["name"],
            "employee_role": matching_emp_row["role"],
            "conflict_posted_entries": posted_eids,
        })

    all_shared_payments = ledger_df[ledger_df["vendor_id"].isin(shared_vendor_ids)]
    all_shared_eids = sorted(all_shared_payments["entry_id"].astype(str).tolist())
    conflict_posted_eids = sorted(list(set(conflict_posted_eids)))

    flagged_ids = conflict_posted_eids if conflict_poster_only else all_shared_eids
    flagged_amount = float(round(ledger_df[ledger_df["entry_id"].isin(flagged_ids)]["amount_inr"].sum(), 2))

    stats = {
        "shared_bank_vendor_ids": shared_vendor_ids,
        "shared_bank_vendors_count": len(shared_vendor_ids),
        "conflict_pairs": conflict_details,
        "conflict_posted_entries_count": len(conflict_posted_eids),
        "total_vendor_disbursements_inr": float(round(all_shared_payments["amount_inr"].sum(), 2)),
        "flagged_amount_inr": flagged_amount,
        "flagged_entries_count": len(flagged_ids),
    }

    notes = (
        f"Identified {len(shared_vendor_ids)} vendors sharing bank accounts with internal employees. "
        f"{len(conflict_posted_eids)} transactions were posted directly by the conflicted employee. "
        f"Flagged {len(flagged_ids)} entries totaling INR {flagged_amount:,.2f}."
    )

    return {
        "test": "vendor_bank_overlap",
        "flagged_ids": flagged_ids,
        "stats": stats,
        "notes": notes,
        "passed": len(flagged_ids) == 0,
    }
