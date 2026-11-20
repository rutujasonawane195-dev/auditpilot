"""Tests for Phase 5 Policy RAG Retrieval and Policy Agent."""

from pathlib import Path
import pytest

from auditpilot.agents import policy_agent, specialists
from auditpilot.tools.policy import parse_policy_clauses, retrieve_policy

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POLICY_FILE = str(DATA_DIR / "policy.md")


def test_parse_policy_clauses():
    """Verify policy parser extracts all 5 numbered sections."""
    clauses = parse_policy_clauses(POLICY_FILE)
    assert len(clauses) >= 5

    clause_ids = [c["clause_id"] for c in clauses]
    assert "Section 4.1" in clause_ids
    assert "Section 5.2" in clause_ids
    assert "Section 6.3" in clause_ids
    assert "Section 7.1" in clause_ids
    assert "Section 8.4" in clause_ids


def test_retrieve_policy_tool_schema():
    """Verify retrieve_policy conforms to the strict audit tool schema."""
    res = retrieve_policy("authorization limits for payments under 50000", k=3, filepath=POLICY_FILE)
    assert res["test"] == "retrieve_policy"
    assert isinstance(res["flagged_ids"], list)
    assert isinstance(res["stats"], dict)
    assert isinstance(res["notes"], str)
    assert "top_matches" in res["stats"]
    assert len(res["stats"]["top_matches"]) == 3


@pytest.mark.parametrize(
    "query,expected_clause",
    [
        (
            "What is the authorization limit for an accounts manager or payments under 50,000?",
            "Section 4.1",
        ),
        (
            "Can an employee approve a journal entry they personally posted? Segregation of duties",
            "Section 5.2",
        ),
        (
            "What are the vendor KYC requirements for GSTIN and PAN registration?",
            "Section 6.3",
        ),
        (
            "What is the duplicate payment prevention policy for invoices within a 7-day window?",
            "Section 7.1",
        ),
        (
            "Are ledger postings permitted on Sundays or weekend non-business days?",
            "Section 8.4",
        ),
    ],
)
def test_top1_policy_retrieval_accuracy(query: str, expected_clause: str):
    """Verify top-1 retrieval accuracy across the 5 benchmark audit policy queries."""
    res = retrieve_policy(query=query, k=3, filepath=POLICY_FILE)
    assert len(res["stats"]["top_matches"]) > 0
    top_match = res["stats"]["top_matches"][0]
    assert (
        top_match["clause_id"] == expected_clause
    ), f"Query '{query}' expected top-1 {expected_clause}, but got {top_match['clause_id']}"


def test_policy_agent_configuration():
    """Verify policy_agent has proper ADK configuration and tool allocations."""
    assert policy_agent.name == "policy_agent"
    assert policy_agent.model == "gemini-3.8-flash"
    assert policy_agent.output_key == "policy_findings"

    tool_names = {t.__name__ for t in policy_agent.tools}
    assert tool_names == {"check_approval_limits", "retrieve_policy"}

    # Instruction requires exact clause_id and quote citations
    assert "clause_id" in policy_agent.instruction
    assert "retrieve_policy" in policy_agent.instruction


def test_specialists_includes_policy_agent():
    """Verify specialists ParallelAgent includes policy_agent."""
    sub_names = {a.name for a in specialists.sub_agents}
    assert sub_names == {"anomaly_agent", "vendor_agent", "ratio_agent", "policy_agent"}
