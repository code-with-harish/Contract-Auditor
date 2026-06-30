"""
Smart Contract Auditor CLI
Command-line interface for scanning Solidity contracts.
"""

import argparse
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.analysis.static_analyzer import StaticAnalyzer
from app.analysis.ml_ranker import MLVulnerabilityClassifier
from app.analysis.explain import ExplainabilityEngine
from app.analysis.report_generator import ReportGenerator


def analyze_file(filepath: str, output_format: str = "text", output_file: str = None):
    """Analyze a single Solidity file."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        source_code = f.read()

    print(f"\n{'='*60}")
    print(f"  Smart Contract Auditor v1.0.0")
    print(f"  Scanning: {os.path.basename(filepath)}")
    print(f"{'='*60}\n")

    # Initialize modules
    static_analyzer = StaticAnalyzer()
    ml_classifier = MLVulnerabilityClassifier()
    explainability = ExplainabilityEngine()
    report_gen = ReportGenerator()

    # Run analysis
    print("[1/4] Running static analysis...")
    static_findings = static_analyzer.analyze(source_code)
    print(f"       Found {len(static_findings)} potential issues")

    print("[2/4] Running ML classification...")
    ml_results = ml_classifier.predict(source_code, static_findings)
    print(f"       ML analysis complete")

    print("[3/4] Merging and ranking findings...")
    combined = _merge_findings(static_findings, ml_results)
    explained = explainability.explain_findings(source_code, combined)

    print("[4/4] Generating report...")
    risk_summary = _compute_risk_summary(explained)

    report = {
        "contract_name": os.path.basename(filepath),
        "findings": explained,
        "risk_summary": risk_summary,
        "total_issues": len(explained),
        "critical": sum(1 for f in explained if f["severity"] == "Critical"),
        "high": sum(1 for f in explained if f["severity"] == "High"),
        "medium": sum(1 for f in explained if f["severity"] == "Medium"),
        "low": sum(1 for f in explained if f["severity"] == "Low"),
        "informational": sum(1 for f in explained if f["severity"] == "Informational"),
    }

    # Output results
    if output_format == "json":
        result = json.dumps(report, indent=2, default=str)
        if output_file:
            with open(output_file, "w") as f:
                f.write(result)
            print(f"\nJSON report saved to: {output_file}")
        else:
            print(result)

    elif output_format == "html":
        html = report_gen.generate_html_report(report)
        out = output_file or filepath.replace(".sol", "_report.html")
        with open(out, "w") as f:
            f.write(html)
        print(f"\nHTML report saved to: {out}")

    else:
        # Text output
        summary = report_gen.generate_summary(report)
        print(f"\n{summary}")

        if explained:
            print(f"\n{'-'*60}")
            print("DETAILED FINDINGS:")
            print(f"{'-'*60}")
            for i, finding in enumerate(explained, 1):
                severity = finding.get("severity", "Unknown")
                icon = {"Critical": "[!]", "High": "[H]", "Medium": "[M]", "Low": "[L]"}.get(severity, "[i]")
                print(f"\n{icon} #{i}: {finding.get('vulnerability_type', 'Unknown')}")
                print(f"    Severity: {severity} | Confidence: {finding.get('confidence', 0)*100:.1f}%")
                print(f"    Rule: {finding.get('rule_id', 'N/A')}")
                if finding.get("line_number"):
                    print(f"    Line {finding['line_number']}: {finding.get('line_content', '')}")
                print(f"    Fix: {finding.get('remediation', 'N/A')}")
        else:
            print("\nNo vulnerabilities detected. Contract appears safe.")

    return report


def _merge_findings(static_findings, ml_results):
    merged = []
    for finding in static_findings:
        vuln_type = finding.get("vulnerability_type", "unknown")
        ml_confidence = ml_results.get("predictions", {}).get(vuln_type, 0.5)
        original_confidence = finding.get("confidence", 0.5)
        adjusted_confidence = (original_confidence * 0.6) + (ml_confidence * 0.4)
        finding["confidence"] = round(adjusted_confidence, 3)
        finding["ml_confidence"] = round(ml_confidence, 3)
        finding["detection_method"] = "hybrid"
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
    for ml_finding in ml_results.get("additional_findings", []):
        ml_finding["detection_method"] = "ml_only"
        merged.append(ml_finding)
    merged.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return merged


def _compute_risk_summary(findings):
    if not findings:
        return {"overall_risk": "Low", "risk_score": 0, "summary": "No vulnerabilities detected."}
    severity_weights = {"Critical": 10, "High": 7, "Medium": 4, "Low": 2, "Informational": 1}
    total_score = sum(severity_weights.get(f.get("severity", "Low"), 1) * f.get("confidence", 0.5) for f in findings)
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
        "summary": f"Found {len(findings)} potential issues. Overall risk level: {overall}.",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Smart Contract Auditor - AI-powered security analysis for Solidity contracts"
    )
    parser.add_argument("file", nargs="?", help="Solidity file to analyze")
    parser.add_argument("-f", "--format", choices=["text", "json", "html"], default="text", help="Output format")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--batch", nargs="+", help="Analyze multiple files")

    args = parser.parse_args()

    if args.batch:
        print(f"Batch analysis of {len(args.batch)} contracts\n")
        for filepath in args.batch:
            analyze_file(filepath, args.format, args.output)
    elif args.file:
        analyze_file(args.file, args.format, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
