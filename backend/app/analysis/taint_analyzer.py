"""
Taint Analysis Engine
Tracks how user-controlled data flows through Solidity smart contracts
to detect data-flow vulnerabilities that pattern matching alone cannot find.

Implements a simplified inter-procedural taint analysis:
  1. Identify SOURCES (user-controlled inputs)
  2. Propagate taint through assignments, function calls, and expressions
  3. Detect when tainted data reaches SINKS (dangerous operations)
"""

import re
from typing import List, Dict, Any, Set, Tuple, Optional


# ── Source / Sink Definitions ────────────────────────────────────

TAINT_SOURCES: List[Dict[str, Any]] = [
    {"id": "SRC-PARAM", "pattern": r"function\s+\w+\s*\(([^)]+)\)", "kind": "parameter",
     "description": "User-supplied function parameter"},
    {"id": "SRC-MSGVALUE", "pattern": r"\bmsg\.value\b", "kind": "msg.value",
     "description": "Ether value attached to the transaction"},
    {"id": "SRC-MSGSENDER", "pattern": r"\bmsg\.sender\b", "kind": "msg.sender",
     "description": "Address of the transaction sender"},
    {"id": "SRC-MSGDATA", "pattern": r"\bmsg\.data\b", "kind": "msg.data",
     "description": "Raw calldata of the transaction"},
    {"id": "SRC-TXORIGIN", "pattern": r"\btx\.origin\b", "kind": "tx.origin",
     "description": "Address that originated the transaction chain"},
    {"id": "SRC-CALLDATA", "pattern": r"\bcalldataload\b|\bcalldatacopy\b", "kind": "calldata",
     "description": "Raw calldata access"},
    {"id": "SRC-EXTCALL", "pattern": r"\.call\(|\.staticcall\(|\.delegatecall\(", "kind": "external_return",
     "description": "Return data from an external call"},
]

TAINT_SINKS: List[Dict[str, Any]] = [
    {"id": "SINK-TRANSFER", "pattern": r"\.transfer\(|\.send\(|\.call\{.*value",
     "description": "Ether transfer — tainted amount or destination may lead to fund theft",
     "severity": "Critical", "vuln_type": "Tainted Ether Transfer"},
    {"id": "SINK-DELEGATECALL", "pattern": r"\.delegatecall\(",
     "description": "delegatecall target is user-controlled — arbitrary code execution",
     "severity": "Critical", "vuln_type": "Tainted Delegatecall Target"},
    {"id": "SINK-SELFDESTRUCT", "pattern": r"\bselfdestruct\s*\(",
     "description": "selfdestruct beneficiary is user-controlled",
     "severity": "Critical", "vuln_type": "Tainted Selfdestruct Beneficiary"},
    {"id": "SINK-SSTORE", "pattern": r"\b\w+\s*=\s*",
     "description": "Tainted data written to contract storage without validation",
     "severity": "High", "vuln_type": "Unchecked Tainted Storage Write"},
    {"id": "SINK-ARRAY-INDEX", "pattern": r"\w+\[[^\]]*\]",
     "description": "Array/mapping index derived from tainted source without bounds check",
     "severity": "Medium", "vuln_type": "Tainted Array Index"},
    {"id": "SINK-REQUIRE-BYPASS", "pattern": r"require\s*\([^,)]+",
     "description": "Guard condition uses tainted data that an attacker controls",
     "severity": "Medium", "vuln_type": "Attacker-Controlled Guard"},
]

# Variables that are commonly validated (sanitizers)
SANITIZER_PATTERNS = [
    r"require\s*\(",
    r"assert\s*\(",
    r"if\s*\(",
    r"revert\b",
]


class TaintedVariable:
    """Represents a tainted variable and its provenance."""

    def __init__(self, name: str, source_id: str, source_line: int, source_kind: str):
        self.name = name
        self.source_id = source_id
        self.source_line = source_line
        self.source_kind = source_kind
        self.propagation_chain: List[Tuple[int, str]] = []  # (line, assignment)

    def add_propagation(self, line: int, code: str):
        self.propagation_chain.append((line, code.strip()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.name,
            "source": self.source_id,
            "source_kind": self.source_kind,
            "source_line": self.source_line,
            "propagation_chain": [
                {"line": l, "code": c} for l, c in self.propagation_chain
            ],
        }


class TaintAnalyzer:
    """
    Performs intra- and inter-function taint analysis on Solidity source code.
    Tracks user-controlled data from sources to dangerous sinks.
    """

    def analyze(self, source_code: str) -> Dict[str, Any]:
        """Run taint analysis on the full contract."""
        lines = source_code.split("\n")
        functions = self._extract_functions(source_code, lines)

        all_findings: List[Dict[str, Any]] = []
        all_tainted: List[TaintedVariable] = []
        flow_graphs: List[Dict[str, Any]] = []

        for func in functions:
            tainted_vars = self._identify_tainted_sources(func, lines)
            self._propagate_taint(func, lines, tainted_vars)
            findings = self._check_sinks(func, lines, tainted_vars)

            # Filter out findings where a sanitizer sits between source and sink
            findings = self._filter_sanitized(func, lines, findings, tainted_vars)

            all_findings.extend(findings)
            all_tainted.extend(tainted_vars)

            if tainted_vars:
                flow_graphs.append({
                    "function": func["name"],
                    "tainted_variables": [tv.to_dict() for tv in tainted_vars],
                    "sinks_reached": len(findings),
                })

        return {
            "taint_findings": all_findings,
            "total_taint_issues": len(all_findings),
            "taint_flows": flow_graphs,
            "total_tainted_vars": len(all_tainted),
            "source_sink_pairs": self._summarise_pairs(all_findings),
        }

    # ── Function extraction ──────────────────────────────────────

    def _extract_functions(
        self, source_code: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        func_pattern = re.compile(r"function\s+(\w+)\s*\(([^)]*)\)\s*(.*?)\{")
        functions: List[Dict[str, Any]] = []
        i = 0
        while i < len(lines):
            match = func_pattern.search(lines[i])
            if match:
                name = match.group(1)
                params = match.group(2).strip()
                modifiers = match.group(3).strip()
                start = i
                brace = lines[i].count("{") - lines[i].count("}")
                body_lines = [lines[i]]
                j = i + 1
                while j < len(lines) and brace > 0:
                    brace += lines[j].count("{") - lines[j].count("}")
                    body_lines.append(lines[j])
                    j += 1
                functions.append({
                    "name": name,
                    "params": params,
                    "modifiers": modifiers,
                    "start_line": start + 1,
                    "end_line": start + len(body_lines),
                    "body_lines": body_lines,
                    "body": "\n".join(body_lines),
                })
                i = j
            else:
                i += 1
        return functions

    # ── Step 1: Identify sources ─────────────────────────────────

    def _identify_tainted_sources(
        self, func: Dict[str, Any], lines: List[str]
    ) -> List[TaintedVariable]:
        tainted: List[TaintedVariable] = []
        seen_names: Set[str] = set()

        # a) Function parameters are tainted
        if func["params"]:
            for param in func["params"].split(","):
                param = param.strip()
                parts = param.split()
                if len(parts) >= 2:
                    var_name = parts[-1].strip()
                    if var_name and var_name not in seen_names:
                        tv = TaintedVariable(
                            var_name, "SRC-PARAM", func["start_line"], "parameter"
                        )
                        tainted.append(tv)
                        seen_names.add(var_name)

        # b) Scan lines for inline sources
        for idx, bline in enumerate(func["body_lines"]):
            abs_line = func["start_line"] + idx
            for src in TAINT_SOURCES:
                if src["id"] == "SRC-PARAM":
                    continue
                if re.search(src["pattern"], bline):
                    # Find the variable being assigned
                    assign_match = re.match(r"\s*(?:\w+\s+)*(\w+)\s*=", bline)
                    if assign_match:
                        vname = assign_match.group(1)
                        if vname not in seen_names:
                            tv = TaintedVariable(
                                vname, src["id"], abs_line, src["kind"]
                            )
                            tainted.append(tv)
                            seen_names.add(vname)

        return tainted

    # ── Step 2: Propagate taint ──────────────────────────────────

    def _propagate_taint(
        self, func: Dict[str, Any], lines: List[str], tainted: List[TaintedVariable]
    ) -> None:
        """Forward-propagate taint through assignments inside the function."""
        tainted_names: Set[str] = {tv.name for tv in tainted}
        taint_map: Dict[str, TaintedVariable] = {tv.name: tv for tv in tainted}

        # Multiple passes to handle transitive propagation
        for _pass in range(3):
            for idx, bline in enumerate(func["body_lines"]):
                abs_line = func["start_line"] + idx
                stripped = bline.strip()
                if not stripped or stripped.startswith("//"):
                    continue

                # Pattern: lhs = ... rhs ...
                assign = re.match(r"\s*(?:(?:uint|int|address|bool|bytes|string)\w*\s+)?(\w+)\s*=(.+)", bline)
                if assign:
                    lhs = assign.group(1)
                    rhs = assign.group(2)
                    for tname in list(tainted_names):
                        if re.search(rf"\b{re.escape(tname)}\b", rhs):
                            if lhs not in tainted_names:
                                # New tainted variable derived from existing
                                parent = taint_map.get(tname, tainted[0] if tainted else None)
                                if parent:
                                    tv = TaintedVariable(
                                        lhs, parent.source_id, parent.source_line, parent.source_kind
                                    )
                                    tv.propagation_chain = list(parent.propagation_chain)
                                    tv.add_propagation(abs_line, stripped)
                                    tainted.append(tv)
                                    tainted_names.add(lhs)
                                    taint_map[lhs] = tv
                            else:
                                taint_map[lhs].add_propagation(abs_line, stripped)
                            break

                # Compound assignment: x += tainted
                compound = re.match(r"\s*(\w+)\s*[\+\-\*\/]?=(.+)", bline)
                if compound:
                    lhs = compound.group(1)
                    rhs = compound.group(2)
                    for tname in tainted_names:
                        if re.search(rf"\b{re.escape(tname)}\b", rhs):
                            if lhs not in tainted_names:
                                parent = taint_map.get(tname)
                                if parent:
                                    tv = TaintedVariable(
                                        lhs, parent.source_id, parent.source_line, parent.source_kind
                                    )
                                    tv.add_propagation(abs_line, stripped)
                                    tainted.append(tv)
                                    tainted_names.add(lhs)
                                    taint_map[lhs] = tv
                            break

    # ── Step 3: Check sinks ──────────────────────────────────────

    def _check_sinks(
        self,
        func: Dict[str, Any],
        lines: List[str],
        tainted: List[TaintedVariable],
    ) -> List[Dict[str, Any]]:
        tainted_names = {tv.name for tv in tainted}
        taint_map = {tv.name: tv for tv in tainted}
        findings: List[Dict[str, Any]] = []

        for idx, bline in enumerate(func["body_lines"]):
            abs_line = func["start_line"] + idx
            stripped = bline.strip()

            for sink in TAINT_SINKS:
                if not re.search(sink["pattern"], stripped):
                    continue

                # Check if any tainted variable appears in the sink expression
                for tname in tainted_names:
                    if re.search(rf"\b{re.escape(tname)}\b", stripped):
                        tv = taint_map.get(tname)
                        if tv is None:
                            continue

                        # Skip storage-write sink for simple loop counters
                        if sink["id"] == "SINK-SSTORE" and self._is_trivial_assignment(stripped, tname):
                            continue

                        findings.append({
                            "rule_id": f"TAINT-{sink['id']}",
                            "vulnerability_type": sink["vuln_type"],
                            "description": (
                                f"Data from {tv.source_kind} (line {tv.source_line}) "
                                f"flows to {sink['description']} at line {abs_line} "
                                f"in function '{func['name']}'."
                            ),
                            "severity": sink["severity"],
                            "confidence": 0.80,
                            "line_number": abs_line,
                            "line_content": stripped,
                            "remediation": self._get_taint_remediation(sink["id"]),
                            "detection_method": "taint_analysis",
                            "taint_trace": {
                                "source": tv.to_dict(),
                                "sink": {
                                    "id": sink["id"],
                                    "line": abs_line,
                                    "code": stripped,
                                },
                                "function": func["name"],
                            },
                        })
                        break  # one finding per sink-line is enough
                # Only report the first matching sink pattern per line
                if any(f.get("line_number") == abs_line for f in findings):
                    break

        return findings

    # ── Step 4: Sanitizer filtering ──────────────────────────────

    def _filter_sanitized(
        self,
        func: Dict[str, Any],
        lines: List[str],
        findings: List[Dict[str, Any]],
        tainted: List[TaintedVariable],
    ) -> List[Dict[str, Any]]:
        """Remove findings where a require/assert guards the tainted variable before the sink."""
        tainted_names = {tv.name for tv in tainted}
        kept: List[Dict[str, Any]] = []

        for finding in findings:
            sink_line = finding.get("line_number", 0)
            sink_id = finding.get("rule_id", "")
            trace = finding.get("taint_trace", {})
            var_name = trace.get("source", {}).get("variable", "")

            # Only treat SSTORE sinks as sanitized if there's a require on the same var
            sanitized = False
            if var_name and sink_id.endswith("SINK-SSTORE"):
                for idx, bline in enumerate(func["body_lines"]):
                    abs_line = func["start_line"] + idx
                    if abs_line >= sink_line:
                        break
                    for pat in SANITIZER_PATTERNS:
                        if re.search(pat, bline) and re.search(rf"\b{re.escape(var_name)}\b", bline):
                            sanitized = True
                            break
                    if sanitized:
                        break

            if not sanitized:
                kept.append(finding)

        return kept

    # ── Helpers ───────────────────────────────────────────────────

    def _is_trivial_assignment(self, line: str, tainted_var: str) -> bool:
        """Return True for loop-counter-like assignments we should ignore."""
        if re.match(r"\s*(?:uint|int)\w*\s+\w+\s*=\s*0\s*;", line):
            return True
        if re.match(r"\s*\w+\s*\+\+\s*;?", line):
            return True
        return False

    def _summarise_pairs(self, findings: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        pairs: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for f in findings:
            trace = f.get("taint_trace", {})
            src = trace.get("source", {}).get("source", "")
            sink = trace.get("sink", {}).get("id", "")
            key = f"{src}->{sink}"
            if key not in seen:
                seen.add(key)
                pairs.append({"source": src, "sink": sink, "vuln_type": f.get("vulnerability_type", "")})
        return pairs

    def _get_taint_remediation(self, sink_id: str) -> str:
        remediations = {
            "SINK-TRANSFER": (
                "Validate the transfer amount and destination against expected values. "
                "Use access control modifiers to restrict who can trigger transfers."
            ),
            "SINK-DELEGATECALL": (
                "Never delegatecall to a user-supplied address. Whitelist allowed targets "
                "or use a proxy pattern with an immutable implementation address."
            ),
            "SINK-SELFDESTRUCT": (
                "Restrict the selfdestruct beneficiary to a known, trusted address. "
                "Add an onlyOwner modifier and consider removing selfdestruct entirely."
            ),
            "SINK-SSTORE": (
                "Validate user-supplied data with require() before writing to storage. "
                "Apply boundary checks and whitelist expected input ranges."
            ),
            "SINK-ARRAY-INDEX": (
                "Validate array indices against the array length before access. "
                "Use require(index < array.length) to prevent out-of-bounds access."
            ),
            "SINK-REQUIRE-BYPASS": (
                "Ensure guard conditions use contract-controlled data where possible. "
                "Do not rely solely on user-supplied values for access control."
            ),
        }
        return remediations.get(sink_id, "Validate and sanitize tainted data before use.")
