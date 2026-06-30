"""Tests for the gas optimization analyzer."""

from app.analysis.gas_analyzer import GasAnalyzer


def test_analyze_returns_dict(gas_code):
    analyzer = GasAnalyzer()
    result = analyzer.analyze(gas_code)
    assert isinstance(result, dict)
    assert "gas_findings" in result
    assert "total_optimization_opportunities" in result
    assert "gas_efficiency_score" in result


def test_detects_optimizations(gas_code):
    analyzer = GasAnalyzer()
    result = analyzer.analyze(gas_code)
    assert result["total_optimization_opportunities"] >= 1


def test_efficiency_score_range(gas_code):
    analyzer = GasAnalyzer()
    result = analyzer.analyze(gas_code)
    assert 0 <= result["gas_efficiency_score"] <= 100


def test_findings_have_fields(gas_code):
    analyzer = GasAnalyzer()
    result = analyzer.analyze(gas_code)
    for finding in result["gas_findings"]:
        assert "rule_id" in finding
        assert "vulnerability_type" in finding
        assert "description" in finding
        assert "remediation" in finding


def test_empty_code():
    analyzer = GasAnalyzer()
    result = analyzer.analyze("")
    assert result["total_optimization_opportunities"] == 0
    assert result["gas_efficiency_score"] == 100
