"""Parallel Specialists Group."""

from google.adk.agents import ParallelAgent
from auditpilot.agents.anomaly import anomaly_agent
from auditpilot.agents.ratio import ratio_agent
from auditpilot.agents.vendor import vendor_agent

specialists = ParallelAgent(
    name="specialists",
    description="Runs forensic anomaly, vendor integrity, and financial ratio specialists concurrently.",
    sub_agents=[
        anomaly_agent,
        vendor_agent,
        ratio_agent,
    ],
)
