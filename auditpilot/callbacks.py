"""AuditPilot Security Callbacks, Audit Trail Logging, and PII Masking."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Optional

# Mask bank accounts with 9 to 18 digits (e.g. 9100..., 5020...), preserving last 4 digits
BANK_ACCOUNT_PATTERN = re.compile(r"\b\d{5,14}(\d{4})\b")

# Sensitive fields to scrub from logs
SENSITIVE_KEYS = {"api_key", "key", "secret", "token", "password", "authorization", "bearer"}


def mask_bank_accounts(text: str) -> str:
    """Mask sensitive bank account numbers in text before data reaches the LLM.

    Replaces 9 to 18 digit account numbers with '****<last_4>'.

    Args:
        text: Input string potentially containing financial account numbers.

    Returns:
        Sanitized string with masked account numbers.
    """
    if not isinstance(text, str):
        return text
    return BANK_ACCOUNT_PATTERN.sub(r"****\1", text)


def _sanitize_payload(payload: Any) -> Any:
    """Recursively strip sensitive credentials and mask PII in payload dictionaries."""
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED_SECRET]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = _sanitize_payload(v)
            elif isinstance(v, str):
                sanitized[k] = mask_bank_accounts(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(payload, list):
        return [_sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        return mask_bank_accounts(payload)
    return payload


def log_audit_event(
    agent: str,
    tool: str,
    args: Dict[str, Any],
    result: Any,
    trail_path: str = "audit_trail.jsonl",
) -> Dict[str, Any]:
    """Append structured JSON audit event with SHA-256 result hash to append-only log.

    Guarantees:
    - Never logs API keys or credentials.
    - Masks bank account numbers.
    - Provides cryptographic traceability via SHA-256 result hash.

    Args:
        agent: Name of invoking agent.
        tool: Name of executed tool.
        args: Input arguments dictionary.
        result: Tool output dictionary or model result.
        trail_path: Path to audit_trail.jsonl.

    Returns:
        The logged audit event record.
    """
    sanitized_args = _sanitize_payload(args or {})

    # Compute deterministic SHA-256 hash of result
    serialized_result = json.dumps(result, sort_keys=True, default=str)
    result_hash = hashlib.sha256(serialized_result.encode("utf-8")).hexdigest()

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "tool": tool,
        "arguments": sanitized_args,
        "result_hash": result_hash,
    }

    log_file = Path(trail_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    return event


def create_adk_tool_callback(agent_name: str, trail_path: str = "audit_trail.jsonl"):
    """Create an ADK-compliant after_tool_callback hook for logging tool executions."""
    def after_tool_callback(tool: Any, args: Dict[str, Any], context: Any, result: Dict[str, Any]):
        tool_name = getattr(tool, "name", str(tool))
        log_audit_event(
            agent=agent_name,
            tool=tool_name,
            args=args,
            result=result,
            trail_path=trail_path,
        )
        return result
    return after_tool_callback
