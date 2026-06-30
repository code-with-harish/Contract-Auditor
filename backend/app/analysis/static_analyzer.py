"""
Static Analyzer Module
Performs rule-based pattern detection on Solidity smart contracts.
Detects common vulnerabilities from the SWC Registry.
"""

import re
from typing import List, Dict, Any


class StaticAnalyzer:
    """
    Rule-based static analyzer for Solidity smart contracts.
    Checks for common vulnerability patterns defined in the SWC Registry.
    """

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load vulnerability detection rules based on SWC Registry."""
        return [
            {
                "id": "SWC-107",
                "name": "Reentrancy",
                "description": "External call followed by state change can allow reentrancy attacks",
                "pattern": r'\.call\{.*value.*\}|\.call\.value\(|\.transfer\(|\.send\(',
                "state_change_after_call": True,
                "severity": "Critical",
                "confidence": 0.9,
                "remediation": "Use the checks-effects-interactions pattern. Update state variables before making external calls. Consider using ReentrancyGuard from OpenZeppelin.",
                "swc_link": "https://swcregistry.io/docs/SWC-107",
            },
            {
                "id": "SWC-101",
                "name": "Integer Overflow/Underflow",
                "description": "Arithmetic operations without overflow checks can wrap around",
                "pattern": r'(?:balances?\[.*\]|totalSupply|amount|value|balance)\s*(?:\+=|\-=|\+\s|\-\s|\*\s)',
                "check_solidity_version": True,
                "min_safe_version": "0.8.0",
                "severity": "High",
                "confidence": 0.7,
                "remediation": "Use Solidity >=0.8.0 which has built-in overflow checks, or use OpenZeppelin's SafeMath library for older versions.",
                "swc_link": "https://swcregistry.io/docs/SWC-101",
            },
            {
                "id": "SWC-115",
                "name": "Authorization through tx.origin",
                "description": "Using tx.origin for authorization is vulnerable to phishing attacks",
                "pattern": r'tx\.origin',
                "severity": "High",
                "confidence": 0.95,
                "remediation": "Replace tx.origin with msg.sender for authorization checks. tx.origin can be manipulated through intermediary contracts.",
                "swc_link": "https://swcregistry.io/docs/SWC-115",
            },
            {
                "id": "SWC-100",
                "name": "Function Default Visibility",
                "description": "Functions without explicit visibility can be called by anyone",
                "pattern": r'function\s+\w+\s*\([^)]*\)\s*(?!.*(?:public|private|internal|external))',
                "severity": "Medium",
                "confidence": 0.8,
                "remediation": "Always explicitly declare function visibility (public, private, internal, or external).",
                "swc_link": "https://swcregistry.io/docs/SWC-100",
            },
            {
                "id": "SWC-104",
                "name": "Unchecked Call Return Value",
                "description": "Return values of low-level calls must be checked",
                "pattern": r'\.call\(|\.delegatecall\(|\.staticcall\(',
                "check_return": True,
                "severity": "High",
                "confidence": 0.85,
                "remediation": "Always check the return value of low-level calls: (bool success, ) = addr.call(...); require(success);",
                "swc_link": "https://swcregistry.io/docs/SWC-104",
            },
            {
                "id": "SWC-105",
                "name": "Unprotected Ether Withdrawal",
                "description": "Functions that withdraw Ether should be access-controlled",
                "pattern": r'(\.transfer\(|\.send\(|\.call\{.*value)',
                "check_access_control": True,
                "severity": "Critical",
                "confidence": 0.75,
                "remediation": "Add access control modifiers (onlyOwner, require(msg.sender == owner)) to functions that transfer Ether.",
                "swc_link": "https://swcregistry.io/docs/SWC-105",
            },
            {
                "id": "SWC-106",
                "name": "Unprotected SELFDESTRUCT",
                "description": "selfdestruct without proper access control can destroy the contract",
                "pattern": r'selfdestruct\(|suicide\(',
                "severity": "Critical",
                "confidence": 0.9,
                "remediation": "Add strict access control to selfdestruct calls, or avoid using selfdestruct entirely.",
                "swc_link": "https://swcregistry.io/docs/SWC-106",
            },
            {
                "id": "SWC-112",
                "name": "Delegatecall to Untrusted Callee",
                "description": "delegatecall to user-supplied address can execute arbitrary code",
                "pattern": r'\.delegatecall\(',
                "severity": "Critical",
                "confidence": 0.85,
                "remediation": "Avoid delegatecall to user-controlled addresses. Use trusted library contracts only.",
                "swc_link": "https://swcregistry.io/docs/SWC-112",
            },
            {
                "id": "SWC-111",
                "name": "Use of Deprecated Functions",
                "description": "Deprecated Solidity functions may have known issues",
                "pattern": r'\bsha3\b|\.callcode\(|suicide\(|block\.blockhash\(|msg\.gas\b',
                "severity": "Low",
                "confidence": 0.95,
                "remediation": "Replace deprecated functions: sha3->keccak256, callcode->delegatecall, suicide->selfdestruct, block.blockhash->blockhash, msg.gas->gasleft().",
                "swc_link": "https://swcregistry.io/docs/SWC-111",
            },
            {
                "id": "SWC-120",
                "name": "Weak Sources of Randomness",
                "description": "Using block variables for randomness is predictable by miners",
                "pattern": r'block\.timestamp|block\.difficulty|block\.number|blockhash\(',
                "context_check": "random|seed|lottery|winner|roll|dice|bet|gambl",
                "severity": "High",
                "confidence": 0.7,
                "remediation": "Use Chainlink VRF or commit-reveal schemes for secure randomness. Block variables are manipulable by miners.",
                "swc_link": "https://swcregistry.io/docs/SWC-120",
            },
            {
                "id": "SWC-116",
                "name": "Block Timestamp Dependence",
                "description": "Reliance on block.timestamp for critical logic can be manipulated",
                "pattern": r'block\.timestamp|now\b',
                "severity": "Low",
                "confidence": 0.6,
                "remediation": "Avoid using block.timestamp for critical time-sensitive logic. Miners can manipulate it by ~15 seconds.",
                "swc_link": "https://swcregistry.io/docs/SWC-116",
            },
            {
                "id": "SWC-103",
                "name": "Floating Pragma",
                "description": "Contract should lock pragma to specific compiler version",
                "pattern": r'pragma\s+solidity\s*\^',
                "severity": "Informational",
                "confidence": 0.95,
                "remediation": "Lock the pragma to a specific version (e.g., pragma solidity 0.8.20;) instead of using ^.",
                "swc_link": "https://swcregistry.io/docs/SWC-103",
            },
            {
                "id": "SWC-108",
                "name": "State Variable Default Visibility",
                "description": "State variables without explicit visibility default to internal",
                "pattern": r'^\s+(?:uint|int|address|bool|string|bytes|mapping)\w*\s+(?!public|private|internal|constant|immutable)',
                "severity": "Informational",
                "confidence": 0.6,
                "remediation": "Always specify visibility for state variables explicitly.",
                "swc_link": "https://swcregistry.io/docs/SWC-108",
            },
            {
                "id": "SWC-131",
                "name": "Presence of Unused Variables",
                "description": "Unused variables may indicate bugs or incomplete code",
                "pattern": None,
                "custom_check": "unused_vars",
                "severity": "Informational",
                "confidence": 0.5,
                "remediation": "Remove unused variables to reduce gas costs and improve code clarity.",
                "swc_link": "https://swcregistry.io/docs/SWC-131",
            },
            {
                "id": "GAS-001",
                "name": "Gas Optimization: Storage in Loop",
                "description": "Reading/writing storage variables in loops is gas-inefficient",
                "pattern": r'for\s*\(.*\)\s*\{[^}]*(?:storage|\.length)',
                "severity": "Informational",
                "confidence": 0.65,
                "remediation": "Cache storage variables in memory before loops. Use local variables inside loop bodies.",
                "swc_link": None,
            },
        ]

    def analyze(self, source_code: str) -> List[Dict[str, Any]]:
        """Run all static analysis rules against the source code."""
        findings = []
        lines = source_code.split("\n")
        solidity_version = self._extract_solidity_version(source_code)

        for rule in self.rules:
            rule_findings = self._check_rule(rule, source_code, lines, solidity_version)
            findings.extend(rule_findings)

        return findings

    def _check_rule(
        self,
        rule: Dict,
        source_code: str,
        lines: List[str],
        solidity_version: str,
    ) -> List[Dict[str, Any]]:
        """Check a single rule against the source code."""
        findings = []

        # Skip integer overflow check for Solidity >= 0.8.0
        if rule.get("check_solidity_version") and solidity_version:
            if self._version_gte(solidity_version, rule.get("min_safe_version", "0.8.0")):
                return findings

        # Custom checks
        if rule.get("custom_check") == "unused_vars":
            return self._check_unused_variables(source_code, lines, rule)

        pattern = rule.get("pattern")
        if not pattern:
            return findings

        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(pattern, line)
            for match in matches:
                # Context-specific checks
                if rule.get("context_check"):
                    # Check surrounding lines for context
                    context_window = "\n".join(
                        lines[max(0, line_num - 6) : min(len(lines), line_num + 5)]
                    )
                    if not re.search(rule["context_check"], context_window, re.IGNORECASE):
                        continue

                # Check for reentrancy pattern: external call before state change
                if rule.get("state_change_after_call"):
                    if not self._check_reentrancy_pattern(lines, line_num):
                        continue

                # Check for unchecked return values
                if rule.get("check_return"):
                    if self._is_return_checked(lines, line_num):
                        continue

                # Check access control on ether transfers
                if rule.get("check_access_control"):
                    func_name = self._get_enclosing_function(lines, line_num)
                    if self._has_access_control(source_code, func_name):
                        continue

                finding = {
                    "rule_id": rule["id"],
                    "vulnerability_type": rule["name"],
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "confidence": rule["confidence"],
                    "line_number": line_num,
                    "line_content": line.strip(),
                    "matched_pattern": match.group(),
                    "remediation": rule["remediation"],
                    "swc_link": rule.get("swc_link"),
                }
                findings.append(finding)

        return findings

    def _check_reentrancy_pattern(self, lines: List[str], call_line: int) -> bool:
        """Check if there's a state change after an external call."""
        state_change_patterns = [
            r'\w+\s*=\s*',       # assignment
            r'\w+\[.*\]\s*=',    # mapping/array assignment
            r'\w+\s*\+=',        # increment assignment
            r'\w+\s*\-=',        # decrement assignment
        ]
        # Check lines after the call within the same function
        for i in range(call_line, min(call_line + 15, len(lines))):
            line = lines[i]
            if '}' in line and '{' not in line:
                break  # end of block
            for pattern in state_change_patterns:
                if re.search(pattern, line):
                    return True
        return False

    def _is_return_checked(self, lines: List[str], line_num: int) -> bool:
        """Check if the return value of a low-level call is checked."""
        line = lines[line_num - 1]
        # Check if return value is captured: (bool success, ) = addr.call(...)
        if re.search(r'\(.*bool.*\)\s*=', line):
            return True
        # Check previous line for variable assignment
        if line_num > 1:
            prev_line = lines[line_num - 2]
            if re.search(r'\(.*bool.*\)\s*=', prev_line):
                return True
        return False

    def _get_enclosing_function(self, lines: List[str], line_num: int) -> str:
        """Get the name of the function enclosing a given line."""
        for i in range(line_num - 1, -1, -1):
            match = re.search(r'function\s+(\w+)', lines[i])
            if match:
                return match.group(1)
        return ""

    def _has_access_control(self, source_code: str, func_name: str) -> bool:
        """Check if a function has access control modifiers."""
        if not func_name:
            return False
        access_patterns = [
            rf'function\s+{func_name}\s*\([^)]*\)[^{{]*onlyOwner',
            rf'function\s+{func_name}\s*\([^)]*\)[^{{]*onlyAdmin',
            rf'function\s+{func_name}\s*\([^)]*\)[^{{]*require\s*\(\s*msg\.sender',
            rf'function\s+{func_name}\s*\([^)]*\)[^{{]*onlyRole',
        ]
        for pattern in access_patterns:
            if re.search(pattern, source_code, re.DOTALL):
                return True
        return False

    def _check_unused_variables(
        self, source_code: str, lines: List[str], rule: Dict
    ) -> List[Dict[str, Any]]:
        """Check for variables that are declared but never used."""
        findings = []
        # Find variable declarations
        var_pattern = r'(?:uint|int|address|bool|string|bytes)\d*\s+(?:public\s+|private\s+|internal\s+)?(\w+)\s*[;=]'

        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(var_pattern, line)
            for match in matches:
                var_name = match.group(1)
                # Count occurrences (excluding the declaration line)
                count = sum(
                    1
                    for i, l in enumerate(lines, 1)
                    if i != line_num and re.search(rf'\b{var_name}\b', l)
                )
                if count == 0:
                    findings.append(
                        {
                            "rule_id": rule["id"],
                            "vulnerability_type": rule["name"],
                            "description": f"Variable '{var_name}' is declared but never used",
                            "severity": rule["severity"],
                            "confidence": rule["confidence"],
                            "line_number": line_num,
                            "line_content": line.strip(),
                            "matched_pattern": var_name,
                            "remediation": rule["remediation"],
                            "swc_link": rule.get("swc_link"),
                        }
                    )

        return findings

    def _extract_solidity_version(self, source_code: str) -> str:
        """Extract the Solidity version from pragma statement."""
        match = re.search(r'pragma\s+solidity\s*[\^~>=<]*\s*(\d+\.\d+\.\d+)', source_code)
        if match:
            return match.group(1)
        return ""

    def _version_gte(self, version: str, min_version: str) -> bool:
        """Check if version >= min_version."""
        try:
            v_parts = [int(x) for x in version.split(".")]
            m_parts = [int(x) for x in min_version.split(".")]
            return v_parts >= m_parts
        except (ValueError, IndexError):
            return False
