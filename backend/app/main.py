"""
Smart Contract Auditor - FastAPI Backend
Main entry point for the REST API
"""

import uuid
import os
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .analysis.static_analyzer import StaticAnalyzer
from .analysis.ml_ranker import MLVulnerabilityClassifier
from .analysis.explain import ExplainabilityEngine
from .analysis.report_generator import ReportGenerator
from .db.store import AnalysisStore

app = FastAPI(
    title="Smart Contract Auditor",
    description="AI-powered security auditor for Solidity smart contracts",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3002", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize modules
static_analyzer = StaticAnalyzer()
ml_classifier = MLVulnerabilityClassifier()
explainability = ExplainabilityEngine()
report_generator = ReportGenerator()
store = AnalysisStore()


class AnalyzeRequest(BaseModel):
    source_code: str
    contract_name: Optional[str] = "Untitled"


class GitAnalyzeRequest(BaseModel):
    git_url: str


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "modules": {
            "static_analyzer": "active",
            "ml_classifier": "active",
            "explainability": "active",
            "report_generator": "active",
        },
    }


@app.post("/analyze")
async def analyze_contract(
    file: Optional[UploadFile] = File(None),
    source_code: Optional[str] = Form(None),
    contract_name: Optional[str] = Form("Untitled"),
):
    """Analyze a Solidity smart contract for vulnerabilities."""

    if file:
        content = await file.read()
        code = content.decode("utf-8")
        name = file.filename or "Untitled"
    elif source_code:
        code = source_code
        name = contract_name
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either a file upload or source_code in form data",
        )

    # Generate analysis ID
    analysis_id = str(uuid.uuid4())

    # Step 1: Static Analysis
    static_findings = static_analyzer.analyze(code)

    # Step 2: ML-based vulnerability classification and risk scoring
    ml_results = ml_classifier.predict(code, static_findings)

    # Step 3: Combine and rank findings
    combined_findings = _merge_findings(static_findings, ml_results)

    # Step 4: Generate explanations
    explained_findings = explainability.explain_findings(code, combined_findings)

    # Step 5: Generate risk summary
    risk_summary = _compute_risk_summary(explained_findings)

    # Build report
    report = {
        "id": analysis_id,
        "contract_name": name,
        "timestamp": datetime.utcnow().isoformat(),
        "source_code": code,
        "findings": explained_findings,
        "risk_summary": risk_summary,
        "total_issues": len(explained_findings),
        "critical": sum(1 for f in explained_findings if f["severity"] == "Critical"),
        "high": sum(1 for f in explained_findings if f["severity"] == "High"),
        "medium": sum(1 for f in explained_findings if f["severity"] == "Medium"),
        "low": sum(1 for f in explained_findings if f["severity"] == "Low"),
        "informational": sum(
            1 for f in explained_findings if f["severity"] == "Informational"
        ),
    }

    # Store result
    store.save(analysis_id, report)

    return report


@app.post("/analyze/json")
async def analyze_contract_json(request: AnalyzeRequest):
    """Analyze a Solidity smart contract from JSON body."""

    code = request.source_code
    name = request.contract_name

    analysis_id = str(uuid.uuid4())

    static_findings = static_analyzer.analyze(code)
    ml_results = ml_classifier.predict(code, static_findings)
    combined_findings = _merge_findings(static_findings, ml_results)
    explained_findings = explainability.explain_findings(code, combined_findings)
    risk_summary = _compute_risk_summary(explained_findings)

    report = {
        "id": analysis_id,
        "contract_name": name,
        "timestamp": datetime.utcnow().isoformat(),
        "source_code": code,
        "findings": explained_findings,
        "risk_summary": risk_summary,
        "total_issues": len(explained_findings),
        "critical": sum(1 for f in explained_findings if f["severity"] == "Critical"),
        "high": sum(1 for f in explained_findings if f["severity"] == "High"),
        "medium": sum(1 for f in explained_findings if f["severity"] == "Medium"),
        "low": sum(1 for f in explained_findings if f["severity"] == "Low"),
        "informational": sum(
            1 for f in explained_findings if f["severity"] == "Informational"
        ),
    }

    store.save(analysis_id, report)
    return report


@app.get("/report/{analysis_id}")
async def get_report(analysis_id: str):
    """Retrieve a previously generated analysis report."""
    report = store.get(analysis_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/reports")
async def list_reports():
    """List all stored analysis reports."""
    return store.list_all()


@app.post("/analyze/batch")
async def analyze_batch(files: list[UploadFile] = File(...)):
    """Analyze multiple contracts in batch."""
    results = []
    for file in files:
        content = await file.read()
        code = content.decode("utf-8")

        analysis_id = str(uuid.uuid4())
        static_findings = static_analyzer.analyze(code)
        ml_results = ml_classifier.predict(code, static_findings)
        combined_findings = _merge_findings(static_findings, ml_results)
        explained_findings = explainability.explain_findings(code, combined_findings)
        risk_summary = _compute_risk_summary(explained_findings)

        report = {
            "id": analysis_id,
            "contract_name": file.filename,
            "timestamp": datetime.utcnow().isoformat(),
            "findings": explained_findings,
            "risk_summary": risk_summary,
            "total_issues": len(explained_findings),
            "critical": sum(
                1 for f in explained_findings if f["severity"] == "Critical"
            ),
            "high": sum(1 for f in explained_findings if f["severity"] == "High"),
            "medium": sum(1 for f in explained_findings if f["severity"] == "Medium"),
            "low": sum(1 for f in explained_findings if f["severity"] == "Low"),
        }
        store.save(analysis_id, report)
        results.append(report)

    return {"batch_results": results, "total_contracts": len(results)}


def _merge_findings(static_findings: list, ml_results: dict) -> list:
    """Merge static analysis findings with ML predictions."""
    merged = []

    for finding in static_findings:
        vuln_type = finding.get("vulnerability_type", "unknown")
        ml_confidence = ml_results.get("predictions", {}).get(vuln_type, 0.5)

        # Adjust confidence based on ML prediction
        original_confidence = finding.get("confidence", 0.5)
        adjusted_confidence = (original_confidence * 0.6) + (ml_confidence * 0.4)

        finding["confidence"] = round(adjusted_confidence, 3)
        finding["ml_confidence"] = round(ml_confidence, 3)
        finding["detection_method"] = "hybrid"

        # Adjust severity based on ML confidence
        if adjusted_confidence >= 0.85:
            finding["severity"] = "Critical"
        elif adjusted_confidence >= 0.7:
            finding["severity"] = "High"
        elif adjusted_confidence >= 0.5:
            finding["severity"] = "Medium"
        elif adjusted_confidence >= 0.3:
            finding["severity"] = "Low"
        else:
            finding["severity"] = "Informational"

        merged.append(finding)

    # Add any ML-only detections
    for ml_finding in ml_results.get("additional_findings", []):
        ml_finding["detection_method"] = "ml_only"
        merged.append(ml_finding)

    # Sort by confidence descending
    merged.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return merged


def _compute_risk_summary(findings: list) -> dict:
    """Compute overall risk score and summary."""
    if not findings:
        return {
            "overall_risk": "Low",
            "risk_score": 0,
            "summary": "No vulnerabilities detected.",
        }

    severity_weights = {
        "Critical": 10,
        "High": 7,
        "Medium": 4,
        "Low": 2,
        "Informational": 1,
    }

    total_score = sum(
        severity_weights.get(f.get("severity", "Low"), 1)
        * f.get("confidence", 0.5)
        for f in findings
    )

    max_possible = len(findings) * 10
    risk_ratio = total_score / max_possible if max_possible > 0 else 0

    if risk_ratio >= 0.7:
        overall = "Critical"
    elif risk_ratio >= 0.5:
        overall = "High"
    elif risk_ratio >= 0.3:
        overall = "Medium"
    else:
        overall = "Low"

    return {
        "overall_risk": overall,
        "risk_score": round(risk_ratio * 100, 1),
        "total_weighted_score": round(total_score, 1),
        "summary": f"Found {len(findings)} potential issues. Overall risk level: {overall}.",
        "recommendation": _get_recommendation(overall),
    }


def _get_recommendation(risk_level: str) -> str:
    recommendations = {
        "Critical": "URGENT: This contract has critical vulnerabilities that could lead to fund loss. Do NOT deploy without fixing all critical issues.",
        "High": "This contract has significant security concerns. Address all high-severity findings before deployment.",
        "Medium": "This contract has moderate risks. Review and fix medium-severity issues for production readiness.",
        "Low": "This contract has minor issues. Consider addressing them for best practices compliance.",
    }
    return recommendations.get(risk_level, "Review findings and address as appropriate.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
