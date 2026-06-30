"""
Control Flow Graph (CFG) Analyzer
Builds a simplified control flow graph from Solidity source code
and detects complex vulnerability patterns through path analysis.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple


class CFGNode:
    """Represents a node in the control flow graph."""

    def __init__(self, node_id: int, node_type: str, code: str, line_number: int):
        self.id = node_id
        self.type = node_type  # 'entry', 'exit', 'block', 'branch', 'loop', 'call'
        self.code = code
        self.line_number = line_number
        self.successors: List[int] = []
        self.predecessors: List[int] = []
        self.has_external_call = False
        self.has_state_change = False
        self.has_ether_transfer = False
        self.has_access_control = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "code": self.code[:100],
            "line_number": self.line_number,
            "successors": self.successors,
            "predecessors": self.predecessors,
            "properties": {
                "has_external_call": self.has_external_call,
                "has_state_change": self.has_state_change,
                "has_ether_transfer": self.has_ether_transfer,
                "has_access_control": self.has_access_control,
            },
        }


class CFGAnalyzer:
    """
    Builds control flow graphs for Solidity functions and detects
    path-sensitive vulnerability patterns.
    """

    EXTERNAL_CALL_PATTERN = re.compile(
        r'\.call\{|\.call\(|\.delegatecall\(|\.staticcall\(|\.send\(|\.transfer\('
    )
    STATE_CHANGE_PATTERN = re.compile(
        r'(?:\w+\s*=\s*(?!.*==))|(?:\w+\[.*\]\s*=)|(?:\w+\s*\+=)|(?:\w+\s*-=)|(?:delete\s+\w+)'
    )
    ETHER_TRANSFER_PATTERN = re.compile(
        r'\.transfer\(|\.send\(|\.call\{.*value'
    )
    ACCESS_CONTROL_PATTERN = re.compile(
        r'require\s*\(\s*msg\.sender|onlyOwner|onlyAdmin|onlyRole|_checkRole'
    )
    BRANCH_PATTERN = re.compile(r'\b(if|else|require|assert)\b')
    LOOP_PATTERN = re.compile(r'\b(for|while|do)\b')

    def __init__(self):
        self.nodes: List[CFGNode] = []
        self.node_counter = 0

    def analyze(self, source_code: str) -> Dict[str, Any]:
        """Build CFG and detect path-sensitive vulnerabilities."""
        functions = self._extract_functions(source_code)
        all_findings = []
        cfg_summaries = []

        for func in functions:
            self.nodes = []
            self.node_counter = 0
            cfg = self._build_cfg(func)
            cfg_summaries.append({
                "function": func["name"],
                "nodes": len(self.nodes),
                "complexity": self._cyclomatic_complexity(),
                "has_loops": any(n.type == "loop" for n in self.nodes),
                "has_external_calls": any(n.has_external_call for n in self.nodes),
            })
            findings = self._detect_cfg_vulnerabilities(func)
            all_findings.extend(findings)

        return {
            "cfg_summaries": cfg_summaries,
            "cfg_findings": all_findings,
            "total_functions": len(functions),
            "avg_complexity": (
                round(sum(s["complexity"] for s in cfg_summaries) / len(cfg_summaries), 1)
                if cfg_summaries else 0
            ),
        }

    def _extract_functions(self, source_code: str) -> List[Dict[str, Any]]:
        """Extract individual functions from the contract."""
        functions = []
        lines = source_code.split("\n")
        func_pattern = re.compile(
            r'function\s+(\w+)\s*\(([^)]*)\)\s*(.*?)\{'
        )
        i = 0
        while i < len(lines):
            match = func_pattern.search(lines[i])
            if match:
                func_name = match.group(1)
                params = match.group(2)
                modifiers = match.group(3)
                start_line = i + 1
                brace_count = lines[i].count("{") - lines[i].count("}")
                body_lines = [lines[i]]
                j = i + 1
                while j < len(lines) and brace_count > 0:
                    brace_count += lines[j].count("{") - lines[j].count("}")
                    body_lines.append(lines[j])
                    j += 1
                functions.append({
                    "name": func_name,
                    "params": params.strip(),
                    "modifiers": modifiers.strip(),
                    "body": "\n".join(body_lines),
                    "start_line": start_line,
                    "end_line": start_line + len(body_lines) - 1,
                    "lines": body_lines,
                })
                i = j
            else:
                i += 1
        return functions

    def _build_cfg(self, func: Dict[str, Any]) -> List[CFGNode]:
        """Build control flow graph for a function."""
        entry = self._create_node("entry", f"function {func['name']}", func["start_line"])
        lines = func["lines"]

        prev_node = entry
        for idx, line in enumerate(lines[1:], 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped == "{" or stripped == "}":
                continue

            if self.LOOP_PATTERN.search(stripped):
                node_type = "loop"
            elif self.BRANCH_PATTERN.search(stripped):
                node_type = "branch"
            elif self.EXTERNAL_CALL_PATTERN.search(stripped):
                node_type = "call"
            else:
                node_type = "block"

            node = self._create_node(node_type, stripped, func["start_line"] + idx)
            node.has_external_call = bool(self.EXTERNAL_CALL_PATTERN.search(stripped))
            node.has_state_change = bool(self.STATE_CHANGE_PATTERN.search(stripped))
            node.has_ether_transfer = bool(self.ETHER_TRANSFER_PATTERN.search(stripped))
            node.has_access_control = bool(self.ACCESS_CONTROL_PATTERN.search(stripped))

            prev_node.successors.append(node.id)
            node.predecessors.append(prev_node.id)
            prev_node = node

        exit_node = self._create_node("exit", "end", func["end_line"])
        prev_node.successors.append(exit_node.id)
        exit_node.predecessors.append(prev_node.id)

        return self.nodes

    def _create_node(self, node_type: str, code: str, line_number: int) -> CFGNode:
        node = CFGNode(self.node_counter, node_type, code, line_number)
        self.nodes.append(node)
        self.node_counter += 1
        return node

    def _cyclomatic_complexity(self) -> int:
        """Compute cyclomatic complexity: E - N + 2P."""
        edges = sum(len(n.successors) for n in self.nodes)
        nodes = len(self.nodes)
        return edges - nodes + 2

    def _detect_cfg_vulnerabilities(self, func: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect vulnerabilities using control flow analysis."""
        findings = []

        # 1. Detect reentrancy via CFG paths (call before state change)
        findings.extend(self._detect_reentrancy_cfg(func))

        # 2. Detect unbounded loops with external calls (DoS risk)
        findings.extend(self._detect_dos_cfg(func))

        # 3. Detect missing access control on sensitive operations
        findings.extend(self._detect_missing_access_control_cfg(func))

        # 4. High complexity warning
        complexity = self._cyclomatic_complexity()
        if complexity > 10:
            findings.append({
                "rule_id": "CFG-COMPLEXITY",
                "vulnerability_type": "High Complexity",
                "description": f"Function '{func['name']}' has cyclomatic complexity of {complexity}. High complexity increases bug risk.",
                "severity": "Medium" if complexity <= 15 else "High",
                "confidence": 0.7,
                "line_number": func["start_line"],
                "line_content": f"function {func['name']}",
                "remediation": "Refactor into smaller functions to reduce complexity.",
                "detection_method": "cfg_analysis",
            })

        return findings

    def _detect_reentrancy_cfg(self, func: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect reentrancy by finding external calls before state changes in CFG."""
        findings = []
        call_nodes = [n for n in self.nodes if n.has_external_call]
        state_nodes = [n for n in self.nodes if n.has_state_change]

        for call_node in call_nodes:
            for state_node in state_nodes:
                if self._is_reachable(call_node.id, state_node.id):
                    # External call can reach a state change
                    findings.append({
                        "rule_id": "CFG-REENTRANCY",
                        "vulnerability_type": "Reentrancy",
                        "description": f"CFG analysis detected external call at line {call_node.line_number} "
                        f"followed by state change at line {state_node.line_number} in '{func['name']}'",
                        "severity": "Critical",
                        "confidence": 0.92,
                        "line_number": call_node.line_number,
                        "line_content": call_node.code,
                        "remediation": "Move state changes before external calls (checks-effects-interactions pattern).",
                        "detection_method": "cfg_analysis",
                    })
                    break
        return findings

    def _detect_dos_cfg(self, func: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect potential DoS: loops containing external calls."""
        findings = []
        loop_nodes = [n for n in self.nodes if n.type == "loop"]

        for loop_node in loop_nodes:
            # Check if any successor in the loop body has an external call
            reachable = self._get_reachable_nodes(loop_node.id, max_depth=20)
            for rid in reachable:
                r_node = self._get_node(rid)
                if r_node and r_node.has_external_call:
                    findings.append({
                        "rule_id": "CFG-DOS",
                        "vulnerability_type": "Denial of Service",
                        "description": f"Loop at line {loop_node.line_number} contains external call at "
                        f"line {r_node.line_number}. A single failing call can block the entire loop.",
                        "severity": "High",
                        "confidence": 0.8,
                        "line_number": loop_node.line_number,
                        "line_content": loop_node.code,
                        "remediation": "Use pull-over-push pattern. Let users withdraw individually instead of batch transfers.",
                        "detection_method": "cfg_analysis",
                    })
                    break
        return findings

    def _detect_missing_access_control_cfg(self, func: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect sensitive operations without access control checks."""
        findings = []
        has_access_control = any(n.has_access_control for n in self.nodes)
        has_ether_transfer = any(n.has_ether_transfer for n in self.nodes)

        # Check modifiers for access control
        modifiers = func.get("modifiers", "")
        has_modifier_access = bool(
            re.search(r'onlyOwner|onlyAdmin|onlyRole|private|internal', modifiers)
        )

        if has_ether_transfer and not has_access_control and not has_modifier_access:
            transfer_node = next((n for n in self.nodes if n.has_ether_transfer), None)
            if transfer_node:
                findings.append({
                    "rule_id": "CFG-ACCESS",
                    "vulnerability_type": "Access Control",
                    "description": f"Function '{func['name']}' transfers Ether at line {transfer_node.line_number} "
                    f"without any access control check.",
                    "severity": "Critical",
                    "confidence": 0.85,
                    "line_number": transfer_node.line_number,
                    "line_content": transfer_node.code,
                    "remediation": "Add access control modifier (onlyOwner) or require(msg.sender == owner) check.",
                    "detection_method": "cfg_analysis",
                })

        return findings

    def _is_reachable(self, from_id: int, to_id: int) -> bool:
        """Check if to_id is reachable from from_id via successors."""
        visited: Set[int] = set()
        stack = [from_id]
        while stack:
            current = stack.pop()
            if current == to_id and current != from_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            node = self._get_node(current)
            if node:
                stack.extend(node.successors)
        return False

    def _get_reachable_nodes(self, start_id: int, max_depth: int = 50) -> Set[int]:
        """Get all nodes reachable from start_id."""
        visited: Set[int] = set()
        stack = [(start_id, 0)]
        while stack:
            current, depth = stack.pop()
            if depth > max_depth or current in visited:
                continue
            visited.add(current)
            node = self._get_node(current)
            if node:
                for succ in node.successors:
                    stack.append((succ, depth + 1))
        return visited

    def _get_node(self, node_id: int) -> Optional[CFGNode]:
        """Get node by ID."""
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None
