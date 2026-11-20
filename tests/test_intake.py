"""Tests for Phase 3 Intake Agent and Reconciliation Pipeline Gate."""

from pathlib import Path
import pandas as pd
import pytest

from auditpilot.agent import audit_lead, root_agent
from auditpilot.agents.intake import evaluate_intake, intake_agent
from auditpilot.schemas import IntakeSummary

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_intake_agent_configuration():
    """Verify intake_agent is properly configured with ADK specifications."""
    assert intake_agent.name == "intake_agent"
    assert intake_agent.model == "gemini-3.8-flash"
    assert intake_agent.output_key == "intake_summary"
    assert len(intake_agent.tools) == 2

    tool_names = [t.__name__ for t in intake_agent.tools]
    assert "load_ledger" in tool_names
    assert "check_trial_balance" in tool_names


def test_audit_lead_configuration():
    """Verify audit_lead acts as root_agent and includes intake_agent as sub-agent."""
    assert root_agent.name == "audit_lead"
    assert audit_lead.name == "audit_lead"
    sub_agent_names = [a.name for a in root_agent.sub_agents]
    assert "intake_agent" in sub_agent_names


def test_intake_gate_halts_on_planted_gap():
    """Verify that intake check halts on the seeded Rs 50,000 trial balance gap."""
    summary: IntakeSummary = evaluate_intake(
        ledger_path=str(DATA_DIR / "ledger.csv"),
        tb_path=str(DATA_DIR / "trial_balance.csv"),
    )
    assert isinstance(summary, IntakeSummary)
    assert summary.status == "FAILED"
    assert summary.is_balanced is False
    assert summary.imbalance == 50000.0
    assert "TB_GAP_001" in summary.flagged_ids
    assert "PIPELINE HALTED" in summary.notes


def test_intake_gate_passes_on_balanced_fixture(tmp_path: Path):
    """Verify that intake check passes when trial balance is balanced."""
    # Create a balanced mock trial balance fixture
    tb_file = DATA_DIR / "trial_balance.csv"
    tb_df = pd.read_csv(tb_file)

    # Adjust to balance: remove the 50,000 imbalance from Employee Benefit Expenses
    gap_idx = tb_df[tb_df["account"].str.contains("6001 Employee Benefit Expenses")].index[0]
    tb_df.at[gap_idx, "debit"] = round(tb_df.at[gap_idx, "debit"] - 50000.0, 2)

    balanced_tb_path = tmp_path / "balanced_trial_balance.csv"
    tb_df.to_csv(balanced_tb_path, index=False)

    summary: IntakeSummary = evaluate_intake(
        ledger_path=str(DATA_DIR / "ledger.csv"),
        tb_path=str(balanced_tb_path),
    )
    assert summary.status == "PASSED"
    assert summary.is_balanced is True
    assert summary.imbalance == 0.0
    assert len(summary.flagged_ids) == 0
    assert summary.row_count >= 5900
    assert summary.total_spend_inr > 0
