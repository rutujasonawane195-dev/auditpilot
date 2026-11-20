"""AuditPilot Root Orchestrator and Lead Agent."""

from google.adk.agents import Agent
from auditpilot.agents.intake import intake_agent
from auditpilot.agents.risk import risk_agent
from auditpilot.agents.skeptic import skeptic_loop
from auditpilot.agents.specialists import specialists

audit_lead = Agent(
    name="audit_lead",
    model="gemini-3.8-flash",
    description="Lead Audit Partner coordinating intake reconciliation, specialist investigations, risk scoring, skeptic loops, and reporting.",
    instruction=(
        "You are the Audit Lead for AuditPilot. "
        "You supervise the entire financial audit lifecycle. "
        "Sequence of operations: "
        "1. First, invoke `intake_agent` to validate data schemas and reconcile the trial balance. "
        "   If intake_summary reflects status 'FAILED', halt the audit immediately and explain the discrepancy. "
        "2. If intake passes, invoke `specialists` (which runs anomaly_agent, vendor_agent, ratio_agent, and policy_agent in parallel). "
        "3. Once specialists finish, invoke `risk_agent` to consolidate, score, and rank all findings into `ranked_findings`. "
        "4. Invoke `skeptic_loop` (max 3 rounds) to challenge claims, verify entry IDs, and move unsupported claims to `dropped_findings`. "
        "Never calculate numbers inside prompts; rely entirely on specialized agents and deterministic code."
    ),
    sub_agents=[intake_agent, specialists, risk_agent, skeptic_loop],
)

root_agent = audit_lead
