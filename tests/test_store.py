"""Tests for the SQLite analysis store."""

import os
import tempfile
import pytest
from app.db.store import AnalysisStore


@pytest.fixture
def store(tmp_path):
    """Create a store backed by a temp SQLite database."""
    db_path = str(tmp_path / "test_auditor.db")
    return AnalysisStore(db_path=db_path)


@pytest.fixture
def sample_report():
    return {
        "id": "test-001",
        "contract_name": "TestContract.sol",
        "timestamp": "2025-01-01T00:00:00",
        "source_code": "pragma solidity ^0.8.0; contract T {}",
        "findings": [
            {"vulnerability_type": "Reentrancy", "severity": "Critical", "confidence": 0.9}
        ],
        "risk_summary": {"overall_risk": "High", "risk_score": 72.5},
        "total_issues": 1,
        "critical": 1,
        "high": 0,
        "medium": 0,
        "low": 0,
        "informational": 0,
    }


def test_save_and_get(store, sample_report):
    store.save(sample_report)
    result = store.get(sample_report["id"])
    assert result is not None
    assert result["contract_name"] == "TestContract.sol"
    assert result["total_issues"] == 1


def test_get_nonexistent(store):
    result = store.get("nonexistent-id")
    assert result is None


def test_list_all(store, sample_report):
    store.save(sample_report)
    all_reports = store.list_all()
    assert isinstance(all_reports, list)
    assert len(all_reports) >= 1
    assert all_reports[0]["id"] == sample_report["id"]


def test_delete(store, sample_report):
    store.save(sample_report)
    assert store.get(sample_report["id"]) is not None
    store.delete(sample_report["id"])
    assert store.get(sample_report["id"]) is None


def test_get_stats_empty(store):
    stats = store.get_stats()
    assert stats["total_audits"] == 0


def test_get_stats(store, sample_report):
    store.save(sample_report)
    stats = store.get_stats()
    assert stats["total_audits"] == 1
    assert stats["total_critical"] == 1


def test_compare(store, sample_report):
    store.save(sample_report)
    report_b = dict(sample_report, id="test-002", contract_name="ContractB.sol")
    store.save(report_b)
    result = store.compare("test-001", "test-002")
    assert result is not None
    assert "report_a" in result
    assert "report_b" in result
    assert "common_vulnerabilities" in result


def test_compare_nonexistent(store, sample_report):
    store.save(sample_report)
    result = store.compare("test-001", "bad-id")
    assert result is None
