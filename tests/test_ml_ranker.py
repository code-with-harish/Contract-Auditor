"""Tests for the ML vulnerability classifier."""

from app.analysis.ml_ranker import MLVulnerabilityClassifier


def test_predict_returns_expected_keys(vulnerable_code):
    classifier = MLVulnerabilityClassifier()
    static_findings = []
    result = classifier.predict(vulnerable_code, static_findings)
    assert "predictions" in result
    assert "features" in result
    assert isinstance(result["predictions"], dict)


def test_predictions_are_probabilities(vulnerable_code):
    classifier = MLVulnerabilityClassifier()
    result = classifier.predict(vulnerable_code, [])
    for vuln_type, score in result["predictions"].items():
        assert 0 <= score <= 1, f"{vuln_type} score {score} out of range"


def test_features_are_numeric(vulnerable_code):
    classifier = MLVulnerabilityClassifier()
    result = classifier.predict(vulnerable_code, [])
    features = result["features"]
    assert isinstance(features, dict)
    for key, val in features.items():
        assert isinstance(val, (int, float)), f"Feature {key} is not numeric"


def test_additional_findings(vulnerable_code):
    classifier = MLVulnerabilityClassifier()
    result = classifier.predict(vulnerable_code, [])
    assert "additional_findings" in result
    assert isinstance(result["additional_findings"], list)


def test_secure_contract_lower_predictions(vulnerable_code, secure_code):
    classifier = MLVulnerabilityClassifier()
    vuln_result = classifier.predict(vulnerable_code, [])
    sec_result = classifier.predict(secure_code, [])
    vuln_avg = sum(vuln_result["predictions"].values()) / max(len(vuln_result["predictions"]), 1)
    sec_avg = sum(sec_result["predictions"].values()) / max(len(sec_result["predictions"]), 1)
    # secure contract should have equal or lower average prediction score
    assert sec_avg <= vuln_avg + 0.1  # small tolerance


def test_empty_code():
    classifier = MLVulnerabilityClassifier()
    result = classifier.predict("", [])
    assert "predictions" in result
