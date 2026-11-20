"""Tests for Phase 9 Guardrails, Hardening, and Evaluation."""

import json
from pathlib import Path
import tempfile
import pytest

from auditpilot.callbacks import (
    create_adk_tool_callback,
    log_audit_event,
    mask_bank_accounts,
)
from evals.run_eval import (
    load_ground_truth,
    run_evaluation_suite,
    verify_prompt_injection_defense,
    verify_zero_number_drift,
    write_eval_results_markdown,
)

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "auditpilot"


def test_mask_bank_accounts():
    """Verify that financial account numbers are masked to ****<last4>."""
    raw_text = "Vendor account 910012345678 received payment. Another account: 502000987654321."
    masked = mask_bank_accounts(raw_text)
    assert "910012345678" not in masked
    assert "502000987654321" not in masked
    assert "****5678" in masked
    assert "****4321" in masked

    # Short numbers or standard text are not masked
    assert mask_bank_accounts("Invoice #1234 on 2026-03-31") == "Invoice #1234 on 2026-03-31"


def test_log_audit_event_security_scrubbing():
    """Verify log_audit_event redacts secrets and logs cryptographic SHA-256 result hash."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "test_trail.jsonl"
        args = {
            "api_key": "AIzaSySecretApiKey123",
            "account_number": "9100998877665544",
            "memo": "Payment authorization",
        }
        result = {"status": "SUCCESS", "records_flagged": 5}

        event = log_audit_event(
            agent="test_agent",
            tool="test_tool",
            args=args,
            result=result,
            trail_path=str(log_file),
        )

        assert event["agent"] == "test_agent"
        assert event["tool"] == "test_tool"
        assert event["arguments"]["api_key"] == "[REDACTED_SECRET]"
        assert event["arguments"]["account_number"] == "****5544"
        assert "result_hash" in event
        assert len(event["result_hash"]) == 64  # SHA-256 hex length

        # Check append-only file contents
        assert log_file.exists()
        line = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert line["arguments"]["api_key"] == "[REDACTED_SECRET]"
        assert line["result_hash"] == event["result_hash"]


def test_adk_tool_callback():
    """Verify create_adk_tool_callback executes logging and passes through result."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "callback_trail.jsonl"
        callback = create_adk_tool_callback("audit_lead", trail_path=str(log_file))

        class DummyTool:
            name = "dummy_audit_tool"

        tool = DummyTool()
        args = {"threshold": 50000}
        result = {"passed": True, "flagged_ids": []}

        cb_result = callback(tool, args, None, result)
        assert cb_result == result

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["tool"] == "dummy_audit_tool"
        assert record["agent"] == "audit_lead"


def test_ground_truth_isolation():
    """CRITICAL: Verify data/ground_truth.csv is NEVER imported or read in auditpilot source code."""
    for py_file in SRC_DIR.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "ground_truth.csv" not in content, (
            f"Isolation violation: {py_file} references ground_truth.csv!"
        )


def test_full_evaluation_run():
    """Verify evaluation suite runs across iterations, reports 100% recall on planted anomalies."""
    results = run_evaluation_suite(iterations=3)
    assert len(results["iterations"]) == 3

    latest = results["iterations"][-1]
    overall = latest["overall"]
    # All 61 ground truth anomalies must be recalled across tools
    assert overall["recall"] == 1.0
    assert overall["tp"] == 61
    assert overall["fn"] == 0

    # Guardrails checks
    assert results["zero_number_drift"]["passed"] is True
    assert results["prompt_injection_defense"]["passed"] is True

    # Check Markdown report generation
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = Path(tmp_dir) / "results.md"
        write_eval_results_markdown(results, output_path=report_path)
        assert report_path.exists()
        report_content = report_path.read_text(encoding="utf-8")
        assert "AuditPilot Hardened Evaluation Report" in report_content
        assert "100.0%" in report_content
