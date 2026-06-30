"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


SAMPLE_CODE = """
pragma solidity ^0.7.0;
contract Test {
    mapping(address => uint256) public balances;
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount);
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);
        balances[msg.sender] -= amount;
    }
}
"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


def test_analyze_json(client):
    r = client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "Test.sol"})
    assert r.status_code == 200
    data = r.json()
    assert "findings" in data
    assert "risk_summary" in data
    assert "id" in data
    assert data["total_issues"] >= 0


def test_analyze_form(client):
    r = client.post("/analyze", data={"source_code": SAMPLE_CODE, "contract_name": "Test.sol"})
    assert r.status_code == 200
    data = r.json()
    assert "findings" in data


def test_reports_list(client):
    # Analyze first so there's at least one report
    client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "List.sol"})
    r = client.get("/reports")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_report(client):
    r = client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "Get.sol"})
    report_id = r.json()["id"]
    r2 = client.get(f"/report/{report_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == report_id


def test_get_report_not_found(client):
    r = client.get("/report/nonexistent")
    assert r.status_code == 404


def test_stats(client):
    client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "Stats.sol"})
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_audits" in data
    assert data["total_audits"] >= 1


def test_delete_report(client):
    r = client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "Del.sol"})
    report_id = r.json()["id"]
    r2 = client.delete(f"/report/{report_id}")
    assert r2.status_code == 200
    r3 = client.get(f"/report/{report_id}")
    assert r3.status_code == 404


def test_compare(client):
    r1 = client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "A.sol"})
    r2 = client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "B.sol"})
    id_a = r1.json()["id"]
    id_b = r2.json()["id"]
    r = client.get(f"/compare/{id_a}/{id_b}")
    assert r.status_code == 200
    data = r.json()
    assert "report_a" in data
    assert "report_b" in data


def test_html_report(client):
    r = client.post("/analyze/json", json={"source_code": SAMPLE_CODE, "contract_name": "Html.sol"})
    report_id = r.json()["id"]
    r2 = client.get(f"/report/{report_id}/html")
    assert r2.status_code == 200
    assert "text/html" in r2.headers["content-type"]


def test_empty_source_rejected(client):
    r = client.post("/analyze/json", json={"source_code": "", "contract_name": "Empty.sol"})
    # Depending on implementation: might be 422 or 400
    assert r.status_code in (400, 422)
