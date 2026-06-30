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

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def save(self, analysis_id: str, report: Dict[str, Any]) -> None:
        """Save an analysis report."""
        self._store[analysis_id] = report

    def get(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a report by ID."""
        return self._store.get(analysis_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all stored reports (summary only)."""
        summaries = []
        for aid, report in self._store.items():
            summaries.append({
                "id": aid,
                "contract_name": report.get("contract_name", "Unknown"),
                "timestamp": report.get("timestamp", ""),
                "total_issues": report.get("total_issues", 0),
                "critical": report.get("critical", 0),
                "high": report.get("high", 0),
                "medium": report.get("medium", 0),
                "low": report.get("low", 0),
                "risk_score": report.get("risk_summary", {}).get("risk_score", 0),
                "overall_risk": report.get("risk_summary", {}).get("overall_risk", "Unknown"),
            })
        return summaries

    def delete(self, analysis_id: str) -> bool:
        """Delete a report."""
        if analysis_id in self._store:
            del self._store[analysis_id]
            return True
        return False
