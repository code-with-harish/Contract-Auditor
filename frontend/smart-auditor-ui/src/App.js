import React, { useState } from 'react';
import './index.css';

// Sample vulnerable contracts for demo
const SAMPLE_CONTRACTS = {
  "VulnerableBank.sol": `// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract VulnerableBank {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABLE: Reentrancy - external call before state update
    function withdraw(uint256 _amount) public {
        require(balances[msg.sender] >= _amount, "Insufficient balance");
        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= _amount;
    }

    // VULNERABLE: tx.origin authentication
    function transferOwnership(address newOwner) public {
        require(tx.origin == owner, "Not owner");
        owner = newOwner;
    }

    // VULNERABLE: No access control
    function withdrawAll() public {
        uint256 balance = address(this).balance;
        payable(msg.sender).transfer(balance);
    }

    // VULNERABLE: Unprotected selfdestruct
    function destroy() public {
        selfdestruct(payable(msg.sender));
    }

    // VULNERABLE: Unchecked send
    function unsafeSend(address payable _to, uint256 _amount) public {
        _to.send(_amount);
    }

    // VULNERABLE: Weak randomness
    function lottery() public view returns (uint256) {
        uint256 winner = uint256(keccak256(abi.encodePacked(block.timestamp, block.difficulty, msg.sender))) % 100;
        return winner;
    }
}`,
  "VulnerableToken.sol": `// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract VulnerableToken {
    string public name = "VulnToken";
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    address public owner;

    constructor(uint256 _initialSupply) {
        owner = msg.sender;
        totalSupply = _initialSupply;
        balanceOf[msg.sender] = totalSupply;
    }

    // VULNERABLE: No access control on mint
    function mint(address _to, uint256 _amount) public {
        totalSupply += _amount;
        balanceOf[_to] += _amount;
    }

    function transfer(address _to, uint256 _value) public returns (bool) {
        require(balanceOf[msg.sender] >= _value);
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;
        return true;
    }

    // VULNERABLE: tx.origin
    function pause() public {
        require(tx.origin == owner);
    }

    // VULNERABLE: Delegatecall to user address
    function delegateAction(address _target, bytes memory _data) public {
        (bool success, ) = _target.delegatecall(_data);
        require(success);
    }
}`,
  "SecureBank.sol": `// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

contract SecureBank {
    mapping(address => uint256) private balances;
    address public owner;
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "No reentrancy");
        locked = true;
        _;
        locked = false;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        require(msg.value > 0, "Must deposit > 0");
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 _amount) external nonReentrant {
        require(balances[msg.sender] >= _amount, "Insufficient");
        balances[msg.sender] -= _amount;
        (bool success, ) = payable(msg.sender).call{value: _amount}("");
        require(success, "Transfer failed");
    }

    function emergencyWithdraw() external onlyOwner {
        (bool success, ) = payable(owner).call{value: address(this).balance}("");
        require(success);
    }
}`
};

const API_BASE = 'http://localhost:8000';

function App() {
  const [sourceCode, setSourceCode] = useState('');
  const [contractName, setContractName] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedFindings, setExpandedFindings] = useState({});
  const [activeTab, setActiveTab] = useState('analyze'); // analyze | reports

  const handleAnalyze = async () => {
    if (!sourceCode.trim()) {
      setError('Please paste Solidity code or select a sample contract');
      return;
    }
    setLoading(true);
    setError('');
    setReport(null);

    try {
      const response = await fetch(`${API_BASE}/analyze/json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_code: sourceCode,
          contract_name: contractName || 'Untitled.sol',
        }),
      });

      if (!response.ok) throw new Error('Analysis failed');
      const data = await response.json();
      setReport(data);
    } catch (err) {
      setError(`Failed to connect to backend. Make sure the server is running on ${API_BASE}. Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setContractName(file.name);
      const reader = new FileReader();
      reader.onload = (ev) => setSourceCode(ev.target.result);
      reader.readAsText(file);
    }
  };

  const loadSample = (name) => {
    setSourceCode(SAMPLE_CONTRACTS[name]);
    setContractName(name);
  };

  const toggleFinding = (index) => {
    setExpandedFindings(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const getSeverityColor = (severity) => {
    const colors = { Critical: '#ff4757', High: '#ff6b35', Medium: '#ffa502', Low: '#2ed573', Informational: '#1e90ff' };
    return colors[severity] || '#6c757d';
  };

  return (
    <div className="app">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <span className="logo-icon">&#x1f6e1;</span>
          <h1>Smart Contract Auditor</h1>
        </div>
        <div className="navbar-links">
          <a href="#analyze" className={activeTab === 'analyze' ? 'active' : ''} onClick={() => setActiveTab('analyze')}>Analyze</a>
          <a href="#about" className={activeTab === 'about' ? 'active' : ''} onClick={() => setActiveTab('about')}>About</a>
        </div>
      </nav>

      <div className="main-container">
        {/* Upload Section */}
        <div className="upload-section">
          <h2>Analyze Smart Contract</h2>
          <p>Paste your Solidity code below, upload a .sol file, or try a sample contract</p>

          <div className="sample-contracts">
            <span style={{color: '#a0a0b0', fontSize: '0.85rem', alignSelf: 'center'}}>Try samples:</span>
            {Object.keys(SAMPLE_CONTRACTS).map(name => (
              <button key={name} className="sample-btn" onClick={() => loadSample(name)}>
                {name}
              </button>
            ))}
          </div>

          <textarea
            className="code-editor"
            value={sourceCode}
            onChange={(e) => setSourceCode(e.target.value)}
            placeholder={`// Paste your Solidity smart contract code here...\n// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n\ncontract MyContract {\n    // ...\n}`}
            spellCheck="false"
          />

          <div className="upload-actions">
            <button className="btn-primary" onClick={handleAnalyze} disabled={loading || !sourceCode.trim()}>
              {loading ? 'Analyzing...' : 'Scan for Vulnerabilities'}
            </button>
            <div className="file-input-wrapper">
              <button className="btn-secondary" onClick={() => document.getElementById('fileInput').click()}>
                Upload .sol File
              </button>
              <input id="fileInput" type="file" accept=".sol" onChange={handleFileUpload} />
            </div>
            {sourceCode && (
              <button className="btn-secondary" onClick={() => { setSourceCode(''); setContractName(''); setReport(null); }}>
                Clear
              </button>
            )}
          </div>

          {error && <p style={{color: '#ff4757', marginTop: '12px'}}>{error}</p>}
        </div>

        {/* Loading */}
        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <div className="loading-text">Running AI-powered security analysis...</div>
            <div style={{color: '#606080', fontSize: '0.85rem'}}>Static Analysis + ML Classification + Explainability</div>
          </div>
        )}

        {/* Results */}
        {report && !loading && (
          <div className="results-section">
            {/* Risk Summary */}
            <div className="risk-summary">
              <div className="risk-header">
                <div>
                  <h2>Audit Results: {report.contract_name}</h2>
                  <p style={{color: '#a0a0b0', fontSize: '0.9rem'}}>{report.risk_summary?.summary}</p>
                </div>
                <div style={{textAlign: 'right'}}>
                  <div className="risk-score">{report.risk_summary?.risk_score}<span>/100</span></div>
                  <span className={`risk-badge ${report.risk_summary?.overall_risk}`}>
                    {report.risk_summary?.overall_risk} Risk
                  </span>
                </div>
              </div>

              <div className="severity-stats">
                <div className="stat-card critical">
                  <div className="count">{report.critical || 0}</div>
                  <div className="label">Critical</div>
                </div>
                <div className="stat-card high">
                  <div className="count">{report.high || 0}</div>
                  <div className="label">High</div>
                </div>
                <div className="stat-card medium">
                  <div className="count">{report.medium || 0}</div>
                  <div className="label">Medium</div>
                </div>
                <div className="stat-card low">
                  <div className="count">{report.low || 0}</div>
                  <div className="label">Low</div>
                </div>
                <div className="stat-card info">
                  <div className="count">{report.informational || 0}</div>
                  <div className="label">Info</div>
                </div>
              </div>

              {report.risk_summary?.recommendation && (
                <div style={{marginTop: '20px', padding: '12px 16px', background: 'rgba(255,71,87,0.08)', borderRadius: '8px', border: '1px solid rgba(255,71,87,0.2)'}}>
                  <strong style={{color: '#ff4757'}}>Recommendation:</strong>
                  <span style={{color: '#a0a0b0', marginLeft: '8px'}}>{report.risk_summary.recommendation}</span>
                </div>
              )}
            </div>

            {/* Findings */}
            <div className="findings-section">
              <h2>Detailed Findings ({report.total_issues})</h2>

              {report.findings?.map((finding, index) => (
                <div key={index} className={`finding-card ${finding.severity}`}>
                  <div className="finding-header">
                    <span className="finding-title">
                      #{index + 1} {finding.vulnerability_type}
                    </span>
                    <span className={`severity-tag ${finding.severity}`}>{finding.severity}</span>
                  </div>

                  <div className="finding-meta">
                    <span>Rule: {finding.rule_id}</span>
                    {finding.line_number && <span>Line: {finding.line_number}</span>}
                    <span>Confidence: {(finding.confidence * 100).toFixed(1)}%</span>
                    <span>Method: {finding.detection_method}</span>
                  </div>

                  <div className="confidence-bar">
                    <div className="confidence-fill" style={{
                      width: `${finding.confidence * 100}%`,
                      background: getSeverityColor(finding.severity)
                    }}></div>
                  </div>

                  <p className="finding-description" style={{marginTop: '12px'}}>{finding.description}</p>

                  {finding.line_content && (
                    <div className="finding-code">
                      {finding.line_number && <span style={{color: '#666'}}>Line {finding.line_number}: </span>}
                      {finding.line_content}
                    </div>
                  )}

                  <div className="finding-remediation">
                    <h4>Remediation</h4>
                    <p>{finding.remediation}</p>
                  </div>

                  <button className="detail-toggle" onClick={() => toggleFinding(index)}>
                    {expandedFindings[index] ? 'Hide Details' : 'Show Detailed Explanation'}
                  </button>

                  {expandedFindings[index] && finding.explanation && (
                    <div className="finding-details">
                      {finding.explanation.summary && (
                        <div style={{marginBottom: '16px'}}>
                          <h4 style={{color: '#00d4ff', marginBottom: '6px'}}>Summary</h4>
                          <p style={{color: '#a0a0b0', fontSize: '0.9rem', lineHeight: '1.7'}}>{finding.explanation.summary}</p>
                        </div>
                      )}

                      {finding.explanation.attack_scenario && (
                        <div style={{marginBottom: '16px'}}>
                          <h4 style={{color: '#ff6b35', marginBottom: '6px'}}>Attack Scenario</h4>
                          <pre style={{background: '#0a0a1a', padding: '12px', borderRadius: '6px', color: '#e0e0e0', fontSize: '0.85rem', whiteSpace: 'pre-wrap'}}>
                            {finding.explanation.attack_scenario}
                          </pre>
                        </div>
                      )}

                      {finding.explanation.fix_example && (
                        <div style={{marginBottom: '16px'}}>
                          <h4 style={{color: '#2ed573', marginBottom: '6px'}}>Fix Example</h4>
                          <pre style={{background: '#0a0a1a', padding: '12px', borderRadius: '6px', color: '#e0e0e0', fontSize: '0.85rem', whiteSpace: 'pre-wrap', fontFamily: 'JetBrains Mono, monospace'}}>
                            {finding.explanation.fix_example}
                          </pre>
                        </div>
                      )}

                      {finding.explanation.code_context?.code_snippet && (
                        <div style={{marginBottom: '16px'}}>
                          <h4 style={{color: '#ffa502', marginBottom: '6px'}}>Code Context</h4>
                          <pre style={{background: '#0a0a1a', padding: '12px', borderRadius: '6px', color: '#e0e0e0', fontSize: '0.85rem', whiteSpace: 'pre-wrap', fontFamily: 'JetBrains Mono, monospace'}}>
                            {finding.explanation.code_context.code_snippet}
                          </pre>
                        </div>
                      )}

                      {finding.explanation.references?.length > 0 && (
                        <div>
                          <h4 style={{color: '#1e90ff', marginBottom: '6px'}}>References</h4>
                          <ul style={{color: '#a0a0b0', fontSize: '0.85rem', paddingLeft: '20px'}}>
                            {finding.explanation.references.map((ref, i) => (
                              <li key={i}><a href={ref.url} target="_blank" rel="noreferrer" style={{color: '#00d4ff'}}>{ref.title}</a></li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="footer">
        <p>Smart Contract Auditor v1.0.0 | AI-Powered Security Analysis for Solidity Contracts</p>
        <p style={{marginTop: '4px'}}>Built with FastAPI + React + ML Classification</p>
      </footer>
    </div>
  );
}

export default App;
