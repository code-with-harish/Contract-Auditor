"""Tests for the explainability engine."""

from app.analysis.static_analyzer import StaticAnalyzer
from app.analysis.explain import ExplainabilityEngine


def test_explain_findings(vulnerable_code):
    analyzer = StaticAnalyzer()
    findings = analyzer.analyze(vulnerable_code)
    engine = ExplainabilityEngine()
    explained = engine.explain_findings(vulnerable_code, findings)
    assert isinstance(explained, list)
    assert len(explained) == len(findings)


def test_explanation_fields(vulnerable_code):
    analyzer = StaticAnalyzer()
    findings = analyzer.analyze(vulnerable_code)
    engine = ExplainabilityEngine()
    explained = engine.explain_findings(vulnerable_code, findings)
    for finding in explained:
        assert "explanation" in finding
        explanation = finding["explanation"]
        assert "summary" in explanation


def test_empty_findings():
    engine = ExplainabilityEngine()
    result = engine.explain_findings("", [])
    assert result == []
