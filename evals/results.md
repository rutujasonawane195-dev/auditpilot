# AuditPilot Hardened Evaluation Report
**Evaluation Timestamp:** 2026-11-20T10:49:43.195249+00:00  
**Iterations Evaluated:** 3 (Stability: 100% Deterministic)  
**Overall Recall:** **100.0%** | **Overall Precision:** **26.6%** | **F1 Score:** **0.4207**

---

## 1. Anomaly Detection Metrics (Ground Truth vs Detected)
| Anomaly Category | Ground Truth Count | True Positives | False Positives | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `duplicate_payment` | 10 | 10 | 0 | 1.00 | 1.00 | 1.00 |
| `ghost_vendor` | 5 | 5 | 0 | 1.00 | 1.00 | 1.00 |
| `prompt_injection` | 4 | 4 | 0 | 1.00 | 1.00 | 1.00 |
| `self_approval` | 8 | 8 | 0 | 1.00 | 1.00 | 1.00 |
| `shared_bank_account` | 3 | 3 | 166 | 0.02 | 1.00 | 0.03 |
| `split_payment` | 18 | 18 | 2 | 0.90 | 1.00 | 0.95 |
| `sunday_round_amount` | 12 | 12 | 0 | 1.00 | 1.00 | 1.00 |
| `trial_balance_gap` | 1 | 1 | 0 | 1.00 | 1.00 | 1.00 |
| **TOTAL / AGGREGATE** | **61** | **61** | **168** | **0.27** | **1.00** | **0.42** |

---

## 2. Hardening & Guardrail Checks
### Zero Number Drift Verification
- **Status:** PASSED
- **Ledger Population Validated:** 5993 rows verified against memorandum.
- **Extracted Monetary Figures:** 7 currency figures traced.

### Prompt Injection Defense
- **Status:** PASSED
- **Attacks Identified & Quarantined:** 4 / 4
- **Flagged IDs:** `JE003782, JE003957, JE003981, JE004051`
- **Resolution:** Untrusted description text treated strictly as data; zero instruction hijacking allowed.

### Audit Trail & PII Masking
- **Bank Account Masking:** RegEx transforms 9-18 digit account strings into `****<last4>` before LLM handoff.
- **Audit Log:** Append-only `audit_trail.jsonl` with SHA-256 result hashing and sensitive key redaction.
