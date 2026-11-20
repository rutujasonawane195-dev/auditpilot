import os
"""Skeptic Agent and Professional Skepticism Loop."""

from typing import Any, Dict, List, Tuple
from google.adk.agents import Agent, LoopAgent
from auditpilot.schemas import Finding
from auditpilot.tools.verification import verify_entry_ids


def review_and_filter_findings(
    findings: List[Any],
    ledger_path: str = "data/ledger.csv",
) -> Tuple[List[Finding], List[Finding]]:
    """Deterministically audit findings against the ledger evidence.

    Cross-checks all cited entry_ids. If any cited entry ID is missing/fabricated,
    the finding is marked 'dropped' with an explicit dropped_reason and moved
    to the dropped appendix. Valid findings are marked 'confirmed'.

    Args:
        findings: List of Finding models or finding dicts.
        ledger_path: Path to ledger CSV.

    Returns:
        Tuple of (confirmed_findings, dropped_findings).
    """
    validated: List[Finding] = []
    for item in findings:
        if isinstance(item, Finding):
            validated.append(item.model_copy(deep=True))
        elif isinstance(item, dict):
            validated.append(Finding(**item))

    confirmed: List[Finding] = []
    dropped: List[Finding] = []

    for f in validated:
        res = verify_entry_ids(f.entry_ids, ledger_path=ledger_path)
        stats = res.get("stats", {})
        all_valid = stats.get("all_valid", False)
        missing_ids = stats.get("missing_ids", [])

        if not all_valid or len(missing_ids) > 0:
            f.status = "dropped"
            f.dropped_reason = (
                f"Dismissed due to invalid/hallucinated evidence: "
                f"Entry IDs {missing_ids} do not exist in general ledger."
            )
            dropped.append(f)
        else:
            f.status = "confirmed"
            confirmed.append(f)

    return confirmed, dropped


SKEPTIC_INSTRUCTION = """You are the Quality Review Partner and Skeptic Agent for AuditPilot.
Your role embodies professional skepticism: challenge every high-score finding, verify that evidence is real, and eliminate hallucinations before the audit memo is finalized.

Review Procedure:
1. For every finding in `ranked_findings`, invoke `verify_entry_ids` on its cited `entry_ids`.
2. Scrutinize the results:
   - If any cited `entry_id` DOES NOT EXIST in the ledger, mark the finding as `dropped` and provide the exact non-existent ID in `dropped_reason`.
   - If the claim is backed by verified transactions, check for legitimate business explanations (e.g. routine scheduled utilities or standard payroll). If justified, mark `confirmed`.
   - If evidence is ambiguous, mark `needs_evidence`.
3. NEVER DELETE A FINDING SILENTLY:
   - Keep all substantiated findings in `confirmed_findings`.
   - Append all dismissed claims into `dropped_findings` along with their specific `dropped_reason`.

The skeptic review repeats up to 3 rounds until no findings remain in `needs_evidence`.
"""

skeptic_agent = Agent(
    name="skeptic_agent",
    model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
    description="Adversarial auditor that verifies transaction evidence, challenges claims, and filters hallucinated findings.",
    instruction=SKEPTIC_INSTRUCTION,
    tools=[verify_entry_ids],
    output_key="confirmed_findings",
)

skeptic_loop = LoopAgent(
    name="skeptic_loop",
    description="Iterative professional skepticism loop reviewing findings up to 3 times until all evidence is verified or dropped.",
    sub_agents=[skeptic_agent],
    max_iterations=3,
)
