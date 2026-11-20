import os
"""Intake Agent for AuditPilot.

Validates ledger structure and reconciles trial balance debits vs credits.
Acts as a mandatory pipeline gate: FAILED halts downstream audit analysis.
"""

from typing import Optional
from google.adk.agents import Agent
from auditpilot.schemas import IntakeSummary
from auditpilot.tools.reconciliation import check_trial_balance, load_ledger

INTAKE_INSTRUCTION = """You are the Intake Auditor for AuditPilot.
Your sole job is to verify data integrity and reconcile company accounts before forensic analysis begins.

Workflow:
1. Call `load_ledger` to verify required columns, date ranges, null fields, and total transaction volume.
2. Call `check_trial_balance` to verify that general ledger debits equal credits and that expenses tie out.
3. Evaluate the results:
   - If `is_balanced` is False, or debits != credits (imbalance > 0.0), or required columns are missing:
     Set status to "FAILED". Note the exact imbalance amount and cite flagged IDs (e.g., 'TB_GAP_001').
     State clearly: "PIPELINE HALTED: Trial balance does not balance. Forensic auditing cannot proceed on unreconciled books."
   - If debits == credits, all columns present, and no unhandled data integrity flaws exist:
     Set status to "PASSED". Record row count and total spend.
4. Output your conclusion adhering strictly to the `intake_summary` schema.

CRITICAL RULES:
- Never invent numbers or perform arithmetic in prompts. Quote numbers exclusively from tool outputs.
- Any imbalance > 0.0 MUST result in status: FAILED.
"""

intake_agent = Agent(
    name="intake_agent",
    model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
    description="Validates ledger structure and reconciles trial balance before specialist audit analysis.",
    instruction=INTAKE_INSTRUCTION,
    tools=[load_ledger, check_trial_balance],
    output_key="intake_summary",
)


def evaluate_intake(
    ledger_path: str = "data/ledger.csv",
    tb_path: str = "data/trial_balance.csv",
) -> IntakeSummary:
    """Deterministic intake evaluation function reflecting intake_agent's decision logic.

    Used by callbacks, pipeline runners, and tests to deterministically enforce
    the reconciliation gate.
    """
    ledger_res = load_ledger(ledger_path)
    tb_res = check_trial_balance(ledger_path, tb_path)

    missing_cols = ledger_res.get("stats", {}).get("missing_columns", [])
    is_balanced = bool(tb_res.get("stats", {}).get("is_balanced", False))
    imbalance = float(tb_res.get("stats", {}).get("imbalance", 0.0))
    ledger_tied = bool(tb_res.get("stats", {}).get("ledger_tied", False))
    flagged_ids = list(tb_res.get("flagged_ids", []))

    if not is_balanced or len(missing_cols) > 0 or imbalance > 0.0:
        status = "FAILED"
        notes = (
            f"PIPELINE HALTED: Intake check failed. Imbalance: INR {imbalance:,.2f}. "
            f"Balanced={is_balanced}. Missing columns: {missing_cols}. "
            f"Flagged IDs: {flagged_ids}."
        )
    else:
        status = "PASSED"
        row_count = int(ledger_res.get("stats", {}).get("row_count", 0))
        spend = float(ledger_res.get("stats", {}).get("total_spend_inr", 0.0))
        notes = (
            f"Intake check passed: {row_count:,} entries reconciled. "
            f"Total spend: INR {spend:,.2f}. Debits equal Credits."
        )

    return IntakeSummary(
        status=status,
        row_count=int(ledger_res.get("stats", {}).get("row_count", 0)),
        total_spend_inr=float(ledger_res.get("stats", {}).get("total_spend_inr", 0.0)),
        imbalance=imbalance,
        is_balanced=is_balanced,
        ledger_tied=ledger_tied,
        flagged_ids=flagged_ids,
        notes=notes,
    )
