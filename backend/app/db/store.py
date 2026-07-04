"""
In-memory analysis store.
Stores and retrieves analysis reports.
Can be replaced with MongoDB/SQLite for persistence.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime


class AnalysisStore:
    """Simple in-memory store for analysis reports. Replace with MongoDB for production."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path
        self._store: Dict[str, Dict[str, Any]] = {}

    def save(
        self,
        analysis_id: str | Dict[str, Any],
        report: Dict[str, Any] | None = None,
    ) -> None:
        """Save an analysis report."""
        if report is None:
            report = analysis_id
            analysis_id = report["id"]
        self._store[analysis_id] = report

    def get(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a report by ID."""
        return self._store.get(analysis_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all stored reports (summary only)."""
        summaries = []
        for aid, report in self._store.items():
            summaries.append(
                {
                    "id": aid,
                    "contract_name": report.get("contract_name", "Unknown"),
                    "timestamp": report.get("timestamp", ""),
                    "total_issues": report.get("total_issues", 0),
                    "critical": report.get("critical", 0),
                    "high": report.get("high", 0),
                    "medium": report.get("medium", 0),
                    "low": report.get("low", 0),
                    "risk_score": report.get("risk_summary", {}).get("risk_score", 0),
                    "overall_risk": report.get("risk_summary", {}).get(
                        "overall_risk", "Unknown"
                    ),
                }
            )
        return summaries

    def delete(self, analysis_id: str) -> bool:
        """Delete a report."""
        if analysis_id in self._store:
            del self._store[analysis_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate analysis statistics."""
        reports = list(self._store.values())
        return {
            "total_audits": len(reports),
            "total_issues": sum(report.get("total_issues", 0) for report in reports),
            "total_critical": sum(report.get("critical", 0) for report in reports),
            "total_high": sum(report.get("high", 0) for report in reports),
            "total_medium": sum(report.get("medium", 0) for report in reports),
            "total_low": sum(report.get("low", 0) for report in reports),
            "total_informational": sum(
                report.get("informational", 0) for report in reports
            ),
        }

    def compare(self, report_a_id: str, report_b_id: str) -> Optional[Dict[str, Any]]:
        """Compare two reports by vulnerability type."""
        report_a = self.get(report_a_id)
        report_b = self.get(report_b_id)
        if not report_a or not report_b:
            return None

        types_a = {
            finding.get("vulnerability_type")
            for finding in report_a.get("findings", [])
            if finding.get("vulnerability_type")
        }
        types_b = {
            finding.get("vulnerability_type")
            for finding in report_b.get("findings", [])
            if finding.get("vulnerability_type")
        }

        return {
            "report_a": report_a,
            "report_b": report_b,
            "common_vulnerabilities": sorted(types_a & types_b),
            "only_in_a": sorted(types_a - types_b),
            "only_in_b": sorted(types_b - types_a),
        }
