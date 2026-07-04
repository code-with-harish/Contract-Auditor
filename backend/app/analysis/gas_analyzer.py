"""
Gas Optimization Analyzer
Detects gas inefficiency patterns in Solidity smart contracts.
"""

import re
from typing import List, Dict, Any


class GasAnalyzer:
    """
    Analyzes Solidity smart contracts for gas optimization opportunities.
    Identifies patterns that consume excessive gas and suggests improvements.
    """

    def __init__(self):
        self.optimization_rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load gas optimization detection rules."""
        return [
            {
                "id": "GAS-001",
                "name": "Storage Read in Loop",
                "description": "Reading state variables inside loops consumes extra gas per iteration",
                "pattern": r'for\s*\([^)]*\)\s*\{[^}]*(?:this\.|self\.)?(?!memory)[\w]+(?:\[|\.length)',
                "severity": "Medium",
                "savings": "100-1000 gas per iteration",
                "remediation": "Cache storage variables in memory before the loop.",
            },
            {
                "id": "GAS-002",
                "name": "Redundant State Access",
                "description": "Accessing the same state variable multiple times instead of caching it",
                "pattern": r'balances\[.*?\].*balances\[.*?\]|totalSupply.*totalSupply',
                "severity": "Low",
                "savings": "200 gas per redundant read",
                "remediation": "Store state variables in local variables and reuse them.",
            },
            {
                "id": "GAS-003",
                "name": "String Concatenation in Loop",
                "description": "Creating strings inside loops is gas-inefficient",
                "pattern": r'for\s*\([^)]*\)\s*\{[^}]*string\s|for\s*\([^)]*\)\s*\{[^}]*\+\s*"',
                "severity": "Medium",
                "savings": "500-2000 gas per iteration",
                "remediation": "Build strings outside the loop or use bytes32 if possible.",
            },
            {
                "id": "GAS-004",
                "name": "Unnecessary Function Calls",
                "description": "Calling functions that return constants from inside loops",
                "pattern": r'for\s*\([^)]*\)\s*\{[^}]*\(\)',
                "severity": "Low",
                "savings": "200-500 gas per call",
                "remediation": "Cache function results or extract them outside the loop.",
            },
            {
                "id": "GAS-005",
                "name": "Array Length in Loop Condition",
                "description": "Reading array length in loop condition (.length) is gas-inefficient",
                "pattern": r'for\s*\([^;]*;\s*[^;]*\.length\s*[<>;]|while\s*\([^)]*\.length|require\s*\([^,]+,\s*"[^"]+"\s*\)',
                "severity": "Medium",
                "savings": "3 gas per iteration",
                "remediation": "Cache the array length in a local variable before the loop.",
            },
            {
                "id": "GAS-006",
                "name": "Public Function Instead of External",
                "description": "Using public instead of external for functions that are never called internally",
                "pattern": r'function\s+\w+\s*\([^)]*\)\s+public(?!\s+view)(?!\s+pure)',
                "severity": "Low",
                "savings": "200-600 gas per call",
                "remediation": "Use external visibility if the function is not called internally.",
            },
            {
                "id": "GAS-007",
                "name": "Multiple msg.sender Accesses",
                "description": "Accessing msg.sender multiple times in the same function",
                "pattern": r'msg\.sender.*msg\.sender',
                "severity": "Low",
                "savings": "20 gas per redundant access",
                "remediation": "Store msg.sender in a local variable and reuse it.",
            },
        ]

    def analyze(self, source_code: str) -> Dict[str, Any]:
        """
        Analyze source code for gas optimization opportunities.
        Returns a dictionary with findings and efficiency score.
        """
        findings = []
        lines = source_code.split("\n")

        for rule in self.optimization_rules:
            pattern = rule.get("pattern")
            if not pattern:
                continue

            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    finding = {
                        "rule_id": rule["id"],
                        "vulnerability_type": rule["name"],
                        "description": rule["description"],
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "severity": rule["severity"],
                        "potential_savings": rule["savings"],
                        "remediation": rule["remediation"],
                    }
                    findings.append(finding)

        # Calculate efficiency score (0-100, higher is better)
        max_possible_issues = len(lines) * len(self.optimization_rules)
        efficiency_score = max(0, 100 - (len(findings) * 10)) if findings else 100

        return {
            "gas_findings": findings,
            "total_optimization_opportunities": len(findings),
            "gas_efficiency_score": efficiency_score,
        }
