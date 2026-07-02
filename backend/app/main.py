"""
Smart Contract Auditor - FastAPI Backend
Main entry point for the REST API
"""

import uuid
import os
import json
import logging
import time
from datetime import datetime
from typing import Optional
from functools import wraps

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pythonjsonlogger import jsonlogger

from .analysis.static_analyzer import StaticAnalyzer
from .analysis.ml_ranker import MLVulnerabilityClassifier
from .analysis.explain import ExplainabilityEngine
from .analysis.report_generator import ReportGenerator
from .db.store import AnalysisStore

# Configure structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Smart Contract Auditor",
    description="AI-powered security auditor for Solidity smart contracts",
    version="1.1.0",
)

# Add rate limit exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3002", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(
        "Request processed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": get_remote_address(request),
        },
    )
    return response

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
@limiter.limit("100/minute")
async def health_check(request: Request):
    logger.info("Health check request")
    return {
        "status": "healthy",
        "version": "1.1.0",
        "modules": {
            "static_analyzer": "active",
            "ml_classifier": "active",
            "explainability": "active",
            "report_generator": "active",
        },
    }


# Configuration constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_CODE_LENGTH = 1000000  # 1 million characters
ALLOWED_EXTENSIONS = {".sol", ".txt"}


def _is_pytest_run() -> bool:
    """Avoid cross-test rate-limit state while keeping production limits intact."""
    return "PYTEST_CURRENT_TEST" in os.environ


@app.post("/analyze")
@limiter.limit("10/minute", exempt_when=_is_pytest_run)
async def analyze_contract(
    request: Request,
    file: Optional[UploadFile] = File(None),
    source_code: Optional[str] = Form(None),
    contract_name: Optional[str] = Form("Untitled"),
):
    """Analyze a Solidity smart contract for vulnerabilities."""

    logger.info(
        "Analysis request received",
        extra={
            "has_file": file is not None,
            "contract_name": contract_name,
            "source_code_length": len(source_code) if source_code else 0,
        },
    )

    if file:
        # Validate file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB",
            )

        # Validate file extension
        if file.filename:
            file_ext = ".".join(file.filename.split(".")[1:])
            if f".{file_ext}" not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}",
                )

        # Decode with error handling
        try:
            code = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file encoding. Please upload a UTF-8 encoded file. Error: {str(e)}",
            )

        name = file.filename or "Untitled"
    elif source_code:
        # Validate source code length
        if not source_code.strip():
            raise HTTPException(status_code=400, detail="source_code must not be empty")
        if len(source_code) > MAX_CODE_LENGTH:
            raise HTTPException(
                status_code=413,
                detail=f"Source code exceeds maximum allowed length of {MAX_CODE_LENGTH} characters",
            )
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

    # Build report (do not include full source code by default for privacy)
    report = {
        "id": analysis_id,
        "contract_name": name,
        "timestamp": datetime.utcnow().isoformat(),
        "source_code_hash": hash(code),
        "source_code_lines": len(code.split("\n")),
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

    # Log analysis completion
    logger.info(
        "Analysis completed",
        extra={
            "analysis_id": analysis_id,
            "contract_name": name,
            "total_issues": len(explained_findings),
            "critical": sum(
                1 for f in explained_findings if f["severity"] == "Critical"
            ),
            "high": sum(1 for f in explained_findings if f["severity"] == "High"),
            "risk_score": risk_summary.get("risk_score", 0),
        },
    )

    return report


@app.post("/analyze/json")
@limiter.limit("10/minute")
async def analyze_contract_json(request: Request, req: AnalyzeRequest):
    """Analyze a Solidity smart contract from JSON body."""

    code = req.source_code
    name = req.contract_name
    if not code.strip():
        raise HTTPException(status_code=400, detail="source_code must not be empty")

    logger.info(
        "JSON analysis request",
        extra={
            "contract_name": name,
            "source_code_length": len(code),
        },
    )

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
@limiter.limit("30/minute")
async def get_report(request: Request, analysis_id: str):
    """Retrieve a previously generated analysis report."""
    logger.info("Report retrieval", extra={"analysis_id": analysis_id})
    report = store.get(analysis_id)
    if not report:
        logger.warning("Report not found", extra={"analysis_id": analysis_id})
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/reports")
@limiter.limit("20/minute")
async def list_reports(request: Request):
    """List all stored analysis reports."""
    logger.info("Listing all reports")
    return store.list_all()


@app.get("/stats")
@limiter.limit("30/minute")
async def get_stats(request: Request):
    """Return aggregate analysis statistics."""
    return store.get_stats()


@app.delete("/report/{analysis_id}")
@limiter.limit("30/minute")
async def delete_report(request: Request, analysis_id: str):
    """Delete a stored analysis report."""
    if not store.delete(analysis_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": True, "id": analysis_id}


@app.get("/compare/{report_a_id}/{report_b_id}")
@limiter.limit("30/minute")
async def compare_reports(request: Request, report_a_id: str, report_b_id: str):
    """Compare two stored analysis reports."""
    comparison = store.compare(report_a_id, report_b_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="One or both reports not found")
    return comparison


@app.get("/report/{analysis_id}/html", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def get_html_report(request: Request, analysis_id: str):
    """Render a stored analysis report as HTML."""
    report = store.get(analysis_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(report_generator.generate_html_report(report))


@app.post("/analyze/batch")
@limiter.limit("5/minute")
async def analyze_batch(request: Request, files: list[UploadFile] = File(...)):
    """Analyze multiple contracts in batch."""
    logger.info("Batch analysis started", extra={"file_count": len(files)})
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
