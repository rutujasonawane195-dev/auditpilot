"""Financial Statement Ratio Analytics."""

from pathlib import Path
from typing import Any, Dict, List
import pandas as pd


def ratio_table(filepath: str = "data/financials.csv") -> Dict[str, Any]:
    """Compute financial statement ratios and monitor month-over-month variances.

    Calculates Gross Margin, Operating Margin, Current Ratio, and Debt-to-Equity.

    Args:
        filepath: Path to financials CSV file.

    Returns:
        Dict with test name, flagged_ids (anomalous months), stats, auditor notes, and passed boolean.
    """
    path = Path(filepath)
    if not path.exists():
        return {
            "test": "ratio_table",
            "flagged_ids": [],
            "stats": {"error": f"Financials file not found: {filepath}"},
            "notes": "Failed: Financials file missing.",
            "passed": False,
        }

    df = pd.read_csv(path)
    monthly_metrics: List[Dict[str, Any]] = []
    flagged_months: List[str] = []

    for _, row in df.iterrows():
        month = str(row["month"])
        rev = float(row["revenue"])
        cogs = float(row["cogs"])
        opex = float(row["opex"])
        ca = float(row["current_assets"])
        cl = float(row["current_liabilities"])
        debt = float(row["debt"])
        equity = float(row["equity"])

        gross_margin = round((rev - cogs) / rev, 4) if rev > 0 else 0.0
        operating_margin = round((rev - cogs - opex) / rev, 4) if rev > 0 else 0.0
        current_ratio = round(ca / cl, 4) if cl > 0 else 0.0
        debt_to_equity = round(debt / equity, 4) if equity > 0 else 0.0

        # Flag any liquidity distress (current ratio < 1.0) or severe margin compression (< 15%)
        if current_ratio < 1.0 or gross_margin < 0.15:
            flagged_months.append(month)

        monthly_metrics.append({
            "month": month,
            "revenue": rev,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "current_ratio": current_ratio,
            "debt_to_equity": debt_to_equity,
        })

    avg_current_ratio = round(sum(m["current_ratio"] for m in monthly_metrics) / len(monthly_metrics), 4) if monthly_metrics else 0.0
    avg_gross_margin = round(sum(m["gross_margin"] for m in monthly_metrics) / len(monthly_metrics), 4) if monthly_metrics else 0.0
    avg_debt_to_equity = round(sum(m["debt_to_equity"] for m in monthly_metrics) / len(monthly_metrics), 4) if monthly_metrics else 0.0

    stats = {
        "months_analyzed": len(monthly_metrics),
        "average_current_ratio": avg_current_ratio,
        "average_gross_margin": avg_gross_margin,
        "average_debt_to_equity": avg_debt_to_equity,
        "monthly_metrics": monthly_metrics,
        "flagged_distress_months": flagged_months,
    }

    notes = (
        f"Analyzed {len(monthly_metrics)} monthly financial statements. "
        f"Average Gross Margin: {avg_gross_margin * 100:.1f}%, "
        f"Average Current Ratio: {avg_current_ratio:.2f}, "
        f"Average Debt-to-Equity: {avg_debt_to_equity:.2f}."
    )

    return {
        "test": "ratio_table",
        "flagged_ids": flagged_months,
        "stats": stats,
        "notes": notes,
        "passed": len(flagged_months) == 0,
    }
