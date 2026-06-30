"""
Explainability Module
Provides human-readable explanations for detected vulnerabilities.
Uses code highlighting, evidence traces, and contextual analysis.
"""

import re
from typing import List, Dict, Any


class ExplainabilityEngine:
    """
    Generates detailed explanations for each vulnerability finding.
    Provides code context, attack scenarios, and evidence traces.
    """

    def explain_findings(
        self, source_code: str, findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add detailed explanations to each finding."""
        lines = source_code.split("\n")
        explained = []

        for finding in findings:
            explanation = self._generate_explanation(finding, lines, source_code)
            finding["explanation"] = explanation
            explained.append(finding)

        return explained

    def _generate_explanation(
        self, finding: Dict[str, Any], lines: List[str], source_code: str
    ) -> Dict[str, Any]:
        """Generate a comprehensive explanation for a single finding."""
        vuln_type = finding.get("vulnerability_type", "")
        line_num = finding.get("line_number")

        explanation = {
            "summary": self._get_summary(vuln_type),
            "attack_scenario": self._get_attack_scenario(vuln_type),
            "evidence": self._get_evidence(finding, lines),
            "code_context": self._get_code_context(lines, line_num) if line_num else None,
            "affected_functions": self._get_affected_functions(lines, line_num) if line_num else [],
            "references": self._get_references(vuln_type),
            "fix_example": self._get_fix_example(vuln_type),
        }

        return explanation

    def _get_summary(self, vuln_type: str) -> str:
        """Get a human-readable summary of the vulnerability."""
        summaries = {
            "Reentrancy": (
                "A reentrancy vulnerability occurs when an external call is made before "
                "internal state changes are completed. An attacker can recursively call back "
                "into the vulnerable function before the first execution is finished, "
                "potentially draining funds. This was the root cause of the infamous DAO hack "
                "in 2016 which led to a loss of ~$60M."
            ),
            "Integer Overflow/Underflow": (
                "Integer overflow/underflow occurs when arithmetic operations exceed the "
                "maximum or minimum value that a fixed-size integer can hold. In Solidity "
                "versions prior to 0.8.0, this silently wraps around, potentially allowing "
                "attackers to manipulate balances or bypass checks."
            ),
            "Authorization through tx.origin": (
                "Using tx.origin for authorization is dangerous because it refers to the "
                "original sender of the transaction, not the immediate caller. An attacker "
                "can trick a user into calling a malicious contract that then calls the "
                "vulnerable contract, passing the tx.origin check."
            ),
            "Unchecked Call Return Value": (
                "Low-level calls (.call(), .send(), .delegatecall()) return a boolean "
                "indicating success or failure. If this return value is not checked, the "
                "contract may continue execution assuming the call succeeded when it actually "
                "failed, leading to inconsistent state."
            ),
            "Unprotected Ether Withdrawal": (
                "Functions that transfer Ether without proper access control can be called "
                "by anyone, allowing unauthorized withdrawal of contract funds."
            ),
            "Unprotected SELFDESTRUCT": (
                "The selfdestruct function permanently destroys a contract and sends its "
                "remaining Ether to a designated address. Without access control, anyone "
                "could destroy the contract."
            ),
            "Delegatecall to Untrusted Callee": (
                "delegatecall executes code from another contract in the context of the "
                "calling contract. If the target is user-controlled, an attacker can execute "
                "arbitrary code that modifies the calling contract's storage."
            ),
            "Weak Sources of Randomness": (
                "Block variables (block.timestamp, block.difficulty, blockhash) are "
                "deterministic and can be predicted or manipulated by miners. Using them as "
                "a source of randomness in gambling or lottery contracts is insecure."
            ),
            "Block Timestamp Dependence": (
                "block.timestamp can be slightly manipulated by miners (up to ~15 seconds). "
                "Contracts that use it for time-sensitive logic may be vulnerable."
            ),
            "Floating Pragma": (
                "A floating pragma (^0.x.x) allows compilation with any compatible compiler "
                "version. This can lead to inconsistent behavior across deployments."
            ),
            "Function Default Visibility": (
                "Functions without explicit visibility default to public in older Solidity "
                "versions, potentially exposing internal logic to external callers."
            ),
            "Use of Deprecated Functions": (
                "Deprecated Solidity functions may be removed in future versions or have "
                "known issues. Using modern alternatives ensures compatibility and security."
            ),
            "Front Running": (
                "Front-running occurs when a miner or attacker observes a pending transaction "
                "and submits their own transaction with a higher gas price to execute before it."
            ),
            "Denial of Service": (
                "Denial of Service vulnerabilities can prevent legitimate users from interacting "
                "with the contract, often through unbounded loops or unexpected reverts."
            ),
            "Access Control": (
                "Missing or inadequate access control allows unauthorized users to execute "
                "privileged functions, potentially leading to fund theft or contract manipulation."
            ),
        }
        return summaries.get(vuln_type, f"Potential {vuln_type} vulnerability detected.")

    def _get_attack_scenario(self, vuln_type: str) -> str:
        """Describe a realistic attack scenario."""
        scenarios = {
            "Reentrancy": (
                "1. Attacker deploys a malicious contract with a fallback/receive function.\n"
                "2. Attacker calls the vulnerable withdraw function.\n"
                "3. The contract sends Ether to the attacker before updating balances.\n"
                "4. The attacker's fallback function re-enters the withdraw function.\n"
                "5. Since the balance hasn't been updated, the attacker can withdraw again.\n"
                "6. This repeats until the contract is drained."
            ),
            "Integer Overflow/Underflow": (
                "1. Attacker identifies an arithmetic operation without overflow protection.\n"
                "2. Attacker crafts an input that causes the value to wrap around.\n"
                "3. For overflow: uint8(255) + 1 = 0, bypassing balance checks.\n"
                "4. For underflow: uint8(0) - 1 = 255, creating a huge fake balance.\n"
                "5. Attacker uses the manipulated value to steal funds."
            ),
            "Authorization through tx.origin": (
                "1. Attacker creates a seemingly legitimate contract (e.g., a token sale).\n"
                "2. Victim (contract owner) interacts with the attacker's contract.\n"
                "3. Attacker's contract calls the vulnerable contract.\n"
                "4. tx.origin still points to the victim (original sender).\n"
                "5. The authorization check passes, and the attacker executes privileged actions."
            ),
            "Unchecked Call Return Value": (
                "1. Contract makes a low-level call (e.g., .send() to transfer Ether).\n"
                "2. The call fails silently (recipient reverts or runs out of gas).\n"
                "3. Since the return value isn't checked, execution continues.\n"
                "4. State is updated as if the transfer succeeded.\n"
                "5. Funds are lost or accounting becomes inconsistent."
            ),
            "Unprotected Ether Withdrawal": (
                "1. Attacker discovers a withdraw function without access control.\n"
                "2. Attacker calls the function directly.\n"
                "3. Contract transfers Ether to the attacker.\n"
                "4. All contract funds can be stolen."
            ),
            "Unprotected SELFDESTRUCT": (
                "1. Attacker finds selfdestruct callable without authorization.\n"
                "2. Attacker calls selfdestruct, permanently destroying the contract.\n"
                "3. All remaining Ether is sent to the attacker's address.\n"
                "4. The contract is permanently removed from the blockchain."
            ),
        }
        return scenarios.get(vuln_type, "Specific attack scenario depends on the contract context.")

    def _get_evidence(self, finding: Dict, lines: List[str]) -> Dict[str, Any]:
        """Gather evidence supporting the finding."""
        evidence = {
            "matched_code": finding.get("line_content", ""),
            "pattern_matched": finding.get("matched_pattern", ""),
            "rule_id": finding.get("rule_id", ""),
            "detection_method": finding.get("detection_method", "static"),
        }

        line_num = finding.get("line_number")
        if line_num and lines:
            # Get surrounding code for context
            start = max(0, line_num - 4)
            end = min(len(lines), line_num + 3)
            evidence["surrounding_code"] = [
                {"line": i + 1, "code": lines[i], "is_flagged": (i + 1) == line_num}
                for i in range(start, end)
            ]

        return evidence

    def _get_code_context(self, lines: List[str], line_num: int) -> Dict[str, Any]:
        """Get detailed code context around the flagged line."""
        if not line_num or line_num > len(lines):
            return {}

        start = max(0, line_num - 6)
        end = min(len(lines), line_num + 5)

        return {
            "start_line": start + 1,
            "end_line": end,
            "flagged_line": line_num,
            "code_snippet": "\n".join(
                f"{'>>>' if i + 1 == line_num else '   '} {i + 1}: {lines[i]}"
                for i in range(start, end)
            ),
        }

    def _get_affected_functions(self, lines: List[str], line_num: int) -> List[str]:
        """Identify functions affected by the vulnerability."""
        if not line_num:
            return []

        functions = []
        for i in range(line_num - 1, -1, -1):
            match = re.search(r'function\s+(\w+)', lines[i])
            if match:
                functions.append(match.group(1))
                break

        return functions

    def _get_references(self, vuln_type: str) -> List[Dict[str, str]]:
        """Get relevant references and resources."""
        base_refs = [
            {"title": "SWC Registry", "url": "https://swcregistry.io/"},
            {"title": "Ethereum Smart Contract Best Practices", "url": "https://consensys.github.io/smart-contract-best-practices/"},
        ]

        specific_refs = {
            "Reentrancy": [
                {"title": "The DAO Hack Explained", "url": "https://www.coindesk.com/understanding-dao-hack-journalists"},
                {"title": "OpenZeppelin ReentrancyGuard", "url": "https://docs.openzeppelin.com/contracts/4.x/api/security#ReentrancyGuard"},
            ],
            "Integer Overflow/Underflow": [
                {"title": "Solidity 0.8 Breaking Changes", "url": "https://docs.soliditylang.org/en/v0.8.0/080-breaking-changes.html"},
            ],
        }

        return base_refs + specific_refs.get(vuln_type, [])

    def _get_fix_example(self, vuln_type: str) -> str:
        """Provide a code example showing the fix."""
        fixes = {
            "Reentrancy": """// VULNERABLE:
function withdraw() public {
    uint amount = balances[msg.sender];
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success);
    balances[msg.sender] = 0;  // State change AFTER external call
}

// FIXED (Checks-Effects-Interactions):
function withdraw() public nonReentrant {
    uint amount = balances[msg.sender];
    balances[msg.sender] = 0;  // State change BEFORE external call
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success);
}""",
            "Integer Overflow/Underflow": """// VULNERABLE (Solidity < 0.8.0):
uint8 balance = 255;
balance += 1;  // Wraps to 0!

// FIXED Option 1: Use Solidity >= 0.8.0 (built-in checks)
pragma solidity ^0.8.0;

// FIXED Option 2: Use SafeMath
using SafeMath for uint256;
balance = balance.add(1);  // Reverts on overflow""",
            "Authorization through tx.origin": """// VULNERABLE:
require(tx.origin == owner);

// FIXED:
require(msg.sender == owner);""",
            "Unchecked Call Return Value": """// VULNERABLE:
payable(addr).send(amount);  // Return value ignored

// FIXED:
(bool success, ) = payable(addr).call{value: amount}("");
require(success, "Transfer failed");""",
            "Unprotected Ether Withdrawal": """// VULNERABLE:
function withdraw(uint amount) public {
    payable(msg.sender).transfer(amount);
}

// FIXED:
function withdraw(uint amount) public onlyOwner {
    payable(msg.sender).transfer(amount);
}""",
            "Unprotected SELFDESTRUCT": """// VULNERABLE:
function destroy() public {
    selfdestruct(payable(msg.sender));
}

// FIXED:
function destroy() public onlyOwner {
    selfdestruct(payable(owner));
}""",
        }
        return fixes.get(vuln_type, "// Refer to the remediation suggestion above.")
