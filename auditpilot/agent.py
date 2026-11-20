"""AuditPilot Root Orchestrator and Lead Agent."""

from google.adk.agents import Agent
from auditpilot.agents.intake import intake_agent
from auditpilot.agents.specialists import specialists

audit_lead = Agent(
    name="audit_lead",
    model="gemini-3.8-flash",
    description="Lead Audit Partner coordinating intake reconciliation, specialist investigations, and reporting.",
    instruction=(
        "You are the Audit Lead for AuditPilot. "
        "You supervise the entire financial audit lifecycle. "
        "Sequence of operations: "
        "1. First, invoke `intake_agent` to validate data schemas and reconcile the trial balance. "
        "   If intake_summary reflects status 'FAILED', halt the audit immediately and explain the discrepancy. "
        "2. If intake passes, invoke `specialists` (which runs anomaly_agent, vendor_agent, and ratio_agent in parallel). "
        "Never calculate numbers inside prompts; rely entirely on specialized agents and tools."
    ),
    sub_agents=[intake_agent, specialists],
)

root_agent = audit_lead
