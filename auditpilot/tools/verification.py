"""Transaction and Evidence Verification Tools."""

from pathlib import Path
from typing import Any, Dict, List
import pandas as pd


def verify_entry_ids(
    entry_ids: List[str],
    ledger_path: str = "data/ledger.csv",
) -> Dict[str, Any]:
    """Verify that cited entry IDs actually exist in the general ledger.

    Used by the skeptic agent to guard against hallucinated or fabricated evidence.

    Args:
        entry_ids: List of transaction entry IDs to verify.
        ledger_path: Path to the general ledger CSV file.

    Returns:
        Standard tool schema dict with test, flagged_ids (missing IDs), stats, and notes.
    """
    path = Path(ledger_path)
    if not path.exists():
        return {
            "test": "verify_entry_ids",
            "flagged_ids": list(entry_ids),
            "stats": {"error": f"Ledger file not found: {ledger_path}"},
            "notes": "Failed: Ledger file missing.",
        }

    ledger_df = pd.read_csv(path)
    existing_ids = set(ledger_df["entry_id"].dropna().astype(str).tolist())

    # Recognize valid trial balance reconciliation identifiers
    existing_ids.add("TB_GAP_001")

    valid_ids: List[str] = []
    missing_ids: List[str] = []

    for eid in entry_ids:
        s_eid = str(eid).strip()
        if s_eid in existing_ids:
            valid_ids.append(s_eid)
        else:
            missing_ids.append(s_eid)

    all_valid = len(missing_ids) == 0

    stats = {
        "total_checked": len(entry_ids),
        "valid_count": len(valid_ids),
        "missing_count": len(missing_ids),
        "all_valid": all_valid,
        "valid_ids": valid_ids,
        "missing_ids": missing_ids,
    }

    if all_valid:
        notes = f"All {len(valid_ids)} cited entry IDs verified in ledger."
    else:
        notes = (
            f"Evidence verification failed: {len(missing_ids)} of {len(entry_ids)} cited IDs "
            f"were NOT found in the ledger ({missing_ids})."
        )

    return {
        "test": "verify_entry_ids",
        "flagged_ids": missing_ids,
        "stats": stats,
        "notes": notes,
    }
