"""Tests for the static analyzer module."""

from app.analysis.static_analyzer import StaticAnalyzer


def test_analyzer_returns_list(vulnerable_code):
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    assert isinstance(results, list)


def test_detects_reentrancy(vulnerable_code):
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    vuln_types = [r["vulnerability_type"] for r in results]
    assert any("Reentrancy" in v for v in vuln_types)


def test_detects_tx_origin(vulnerable_code):
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    vuln_types = [r["vulnerability_type"] for r in results]
    assert any("tx.origin" in v.lower() or "Authorization" in v for v in vuln_types)


def test_detects_selfdestruct(vulnerable_code):
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    vuln_types = [r["vulnerability_type"] for r in results]
    assert any("selfdestruct" in v.lower() or "Unprotected" in v for v in vuln_types)


def test_detects_unchecked_send(vulnerable_code):
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    vuln_types = [r["vulnerability_type"] for r in results]
    assert any("Unchecked" in v or "Return" in v for v in vuln_types)


def test_detects_weak_randomness(vulnerable_code):
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    vuln_types = [r["vulnerability_type"] for r in results]
    assert any("Random" in v or "Timestamp" in v or "block" in v.lower() for v in vuln_types)


def test_secure_contract_fewer_issues(vulnerable_code, secure_code):
    analyzer = StaticAnalyzer()
    vuln_results = analyzer.analyze(vulnerable_code)
    secure_results = analyzer.analyze(secure_code)
    assert len(secure_results) < len(vuln_results)


def test_finding_has_required_fields(vulnerable_code):
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    assert len(results) > 0
    for finding in results:
        assert "vulnerability_type" in finding
        assert "severity" in finding
        assert "confidence" in finding
        assert "description" in finding
        assert "rule_id" in finding


def test_empty_code():
    analyzer = StaticAnalyzer()
    results = analyzer.analyze("")
    assert isinstance(results, list)
    assert len(results) == 0


def test_integer_overflow_older_solidity(vulnerable_code):
    """Contracts with pragma <0.8.0 should flag integer overflow."""
    analyzer = StaticAnalyzer()
    results = analyzer.analyze(vulnerable_code)
    vuln_types = [r["vulnerability_type"] for r in results]
    assert any("Overflow" in v or "Integer" in v for v in vuln_types)
