"""AuditPilot Core Schemas and Data Models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FindingSeverity(str, Enum):
    """Severity levels for audit findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingCategory(str, Enum):
    """Audit category classification."""

    RECONCILIATION = "reconciliation"
    JOURNAL_ENTRY = "journal_entry"
    VENDOR_INTEGRITY = "vendor_integrity"
    FINANCIAL_ANALYSIS = "financial_analysis"
    SECURITY = "security"


class Finding(BaseModel):
    """Standardized finding model citing entry_ids as evidence.

    Adheres to AuditPilot internal rule:
    'Every finding must cite entry_ids as evidence.'
    """

    finding_id: str = Field(..., description="Unique finding identifier, e.g. FIND-001")
    title: str = Field(..., description="Short title of the finding")
    category: FindingCategory = Field(..., description="Audit test category")
    severity: FindingSeverity = Field(..., description="Finding severity level")
    description: str = Field(..., description="Auditor narrative and risk rationale")
    entry_ids: List[str] = Field(..., description="Cited entry_ids proving the anomaly")
    amount_inr: float = Field(default=0.0, description="Total monetary exposure in INR")
    recommendation: Optional[str] = Field(default="", description="Audit remediation advice")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Underlying metric evidence")


class AuditToolResult(BaseModel):
    """Uniform output structure for all audit tools."""

    test: str = Field(..., description="Identifier name of the executed audit tool")
    flagged_ids: List[str] = Field(default_factory=list, description="List of flagged entry IDs")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Numeric metrics and statistics")
    notes: str = Field(..., description="Auditor notes summarizing the quantitative findings")
    passed: bool = Field(default=True, description="True if no anomalous items detected")


class LedgerRecord(BaseModel):
    """Schema for individual General Ledger entry."""

    entry_id: str
    date: str
    posted_by: str
    approved_by: str
    account_code: str
    account_name: str
    vendor_id: str
    amount_inr: float
    description: str
