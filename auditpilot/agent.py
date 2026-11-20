"""AuditPilot Root Orchestrator and Lead Agent."""

from google.adk.agents import Agent
from auditpilot.agents.intake import intake_agent

audit_lead = Agent(
    name="audit_lead",
    model="gemini-3.8-flash",
    description="Lead Audit Partner coordinating intake reconciliation, specialist investigations, and reporting.",
    instruction=(
        "You are the Audit Lead for AuditPilot. "
        "Always execute intake verification first using intake_agent. "
        "If intake_summary has status 'FAILED', halt the audit pipeline immediately with a clear error. "
        "Never calculate numbers inside prompts; rely entirely on specialized agents and tools."
    ),
    sub_agents=[intake_agent],
)

root_agent = audit_lead
