import os
"""Risk Scoring and Ranking Agent."""

from typing import Any, Dict, List
from google.adk.agents import Agent
from auditpilot.schemas import Finding, RankedFindings


def score_and_rank_findings(raw_findings: List[Any]) -> RankedFindings:
    """Deterministically score, sort, and aggregate findings by risk score descending.

    Args:
        raw_findings: List of Finding models or finding dictionaries.

    Returns:
        RankedFindings object sorted by score (likelihood * impact) descending.
    """
    validated_findings: List[Finding] = []
    for item in raw_findings:
        if isinstance(item, Finding):
            validated_findings.append(item)
        elif isinstance(item, dict):
            validated_findings.append(Finding(**item))

    # Sort descending by code-computed score, then by amount_at_risk_inr
    ranked = sorted(
        validated_findings,
        key=lambda f: (f.score, f.amount_at_risk_inr),
        reverse=True,
    )

    tot_exposure = float(round(sum(f.amount_at_risk_inr for f in ranked), 2))
    max_score = max((f.score for f in ranked), default=0)

    return RankedFindings(
        findings=ranked,
        total_findings=len(ranked),
        total_exposure_inr=tot_exposure,
        highest_score=max_score,
    )


RISK_INSTRUCTION = """You are the Senior Risk Officer for AuditPilot.
Your mandate is to synthesize findings from all specialist agents (anomaly_findings, vendor_findings, ratio_findings, policy_findings) into a consolidated, ranked risk register.

Risk Scoring Rubric:
- Likelihood (1 to 5):
  1: Remote / single isolated posting
  2: Low / rare occurrence
  3: Moderate / recurring operational pattern
  4: High / systemic control bypass or multiple occurrences
  5: Definite / structured deliberate evasion (e.g. split payments just under threshold, conflict of interest)

- Impact (1 to 5):
  1: Negligible (< INR 10,000)
  2: Low (INR 10,000 to INR 50,000)
  3: Moderate (INR 50,001 to INR 500,000)
  4: High (INR 500,001 to INR 2,000,000 or segregation of duties violation)
  5: Critical (> INR 2,000,000, unverified ghost vendor, or direct internal fraud)

MANDATORY RULES:
- Never perform arithmetic in your prompt. All scores (`likelihood * impact`) and sums are calculated by code.
- Every finding MUST cite at least one `entry_id` from tool evidence.
- Order all findings into `ranked_findings` with the highest risk scores first.
"""

risk_agent = Agent(
    name="risk_agent",
    model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
    description="Consolidates findings from all specialists, assigns likelihood and impact per audit rubric, and outputs ranked findings.",
    instruction=RISK_INSTRUCTION,
    output_key="ranked_findings",
)
