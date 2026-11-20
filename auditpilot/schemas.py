"""AuditPilot Core Schemas and Data Models."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


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
    POLICY_COMPLIANCE = "policy_compliance"
    FINANCIAL_ANALYSIS = "financial_analysis"
    SECURITY = "security"


class Finding(BaseModel):
    """Standardized finding model citing entry_ids as evidence.

    Enforces:
    1. 'Every finding must cite entry_ids as evidence' (len >= 1).
    2. 'Score is computed by code as likelihood * impact' (never in prompt).
    """

    id: str = Field(default="", description="Unique finding ID, e.g. FIND-001")
    finding_id: str = Field(default="", description="Alias for finding ID")
    title: str = Field(..., description="Short title of the finding")
    category: str = Field(default="journal_entry", description="Audit test category")
    entry_ids: List[str] = Field(..., description="Cited entry_ids proving the anomaly")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Underlying metric evidence and citations")
    amount_at_risk_inr: float = Field(default=0.0, description="Total monetary exposure in INR")
    amount_inr: float = Field(default=0.0, description="Alias for amount_at_risk_inr")
    likelihood: int = Field(default=1, ge=1, le=5, description="Likelihood score (1-5)")
    impact: int = Field(default=1, ge=1, le=5, description="Impact score (1-5)")
    score: int = Field(default=1, description="Computed risk score: likelihood * impact (1-25)")
    severity: FindingSeverity | str = Field(default=FindingSeverity.LOW, description="Risk tier: LOW, MEDIUM, HIGH, CRITICAL")
    rationale: str = Field(default="", description="Auditor narrative and risk explanation")
    description: str = Field(default="", description="Alias for rationale")
    recommendation: Optional[str] = Field(default="", description="Remediation guidance")
    dropped_reason: Optional[str] = Field(default="", description="Auditor rationale for dropping or dismissing a finding")
    status: Literal["open", "confirmed", "needs_evidence", "dropped"] = Field(default="open", description="Finding lifecycle status")

    @field_validator("entry_ids")
    @classmethod
    def validate_entry_ids_not_empty(cls, v: List[str]) -> List[str]:
        if not v or len(v) == 0:
            raise ValueError("Every finding must cite at least one entry_id as concrete evidence.")
        return v

    @model_validator(mode="after")
    def compute_scores_and_sync_aliases(self) -> "Finding":
        # Synchronize ID aliases
        if self.finding_id and not self.id:
            self.id = self.finding_id
        elif self.id and not self.finding_id:
            self.finding_id = self.id
        elif not self.id and not self.finding_id:
            self.id = "FIND-UNSET"
            self.finding_id = "FIND-UNSET"

        # Synchronize amounts
        if self.amount_at_risk_inr == 0.0 and self.amount_inr > 0.0:
            self.amount_at_risk_inr = self.amount_inr
        elif self.amount_inr == 0.0 and self.amount_at_risk_inr > 0.0:
            self.amount_inr = self.amount_at_risk_inr

        # Synchronize rationale/description
        if not self.rationale and self.description:
            self.rationale = self.description
        elif not self.description and self.rationale:
            self.description = self.rationale

        # Code computes score: likelihood * impact (1 to 25)
        self.score = int(self.likelihood * self.impact)

        # Assign severity based on standard heat-map tiers if not explicitly provided
        if self.likelihood > 1 or self.impact > 1 or self.severity == FindingSeverity.LOW:
            if self.score >= 20:
                self.severity = FindingSeverity.CRITICAL
            elif self.score >= 15:
                self.severity = FindingSeverity.HIGH
            elif self.score >= 8:
                self.severity = FindingSeverity.MEDIUM
            else:
                self.severity = FindingSeverity.LOW
        elif isinstance(self.severity, str):
            try:
                self.severity = FindingSeverity(self.severity)
            except ValueError:
                pass

        return self


class RankedFindings(BaseModel):
    """Container model holding ordered audit findings sorted by score descending."""

    findings: List[Finding] = Field(default_factory=list, description="Ordered list of findings")
    total_findings: int = Field(default=0, description="Total count of findings")
    total_exposure_inr: float = Field(default=0.0, description="Aggregated exposure amount in INR")
    highest_score: int = Field(default=0, description="Maximum risk score across all findings")


class AuditToolResult(BaseModel):
    """Uniform output structure for all audit tools."""

    test: str = Field(..., description="Identifier name of the executed audit tool")
    flagged_ids: List[str] = Field(default_factory=list, description="List of flagged entry IDs")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Numeric metrics and statistics")
    notes: str = Field(..., description="Auditor notes summarizing the quantitative findings")
    passed: bool = Field(default=True, description="True if no anomalous items detected")


class IntakeSummary(BaseModel):
    """Structured reconciliation summary generated by intake_agent."""

    status: Literal["PASSED", "FAILED"] = Field(..., description="Reconciliation and schema gate status")
    row_count: int = Field(default=0, description="Total ledger rows validated")
    total_spend_inr: float = Field(default=0.0, description="Total expenditure amount verified in INR")
    imbalance: float = Field(default=0.0, description="Debit minus credit imbalance amount")
    is_balanced: bool = Field(default=True, description="True if trial balance debits equal credits")
    ledger_tied: bool = Field(default=True, description="True if ledger expenses match trial balance")
    flagged_ids: List[str] = Field(default_factory=list, description="Flagged entry IDs such as TB_GAP_001")
    notes: str = Field(default="", description="Auditor intake summary and gate rationale")


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
