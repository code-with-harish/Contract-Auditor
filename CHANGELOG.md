# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-01

### Added
- **Gas Optimization Analyzer**: New `GasAnalyzer` module detects 7 common gas inefficiency patterns
  - Storage reads in loops
  - Redundant state access
  - String concatenation in loops
  - Unnecessary function calls
  - Array length checks in loop conditions
  - Public vs external function selection
  - Multiple msg.sender accesses
- **Input Validation**: Comprehensive validation for `/analyze` endpoint
  - File size limits (5MB max)
  - File type validation (.sol, .txt only)
  - Source code length validation (1M chars max)
  - UTF-8 encoding error handling
- **API Documentation**: 
  - Added [CONTRIBUTING.md](CONTRIBUTING.md) with contribution guidelines
  - Added [ISSUES.md](ISSUES.md) documenting tracked issues
  - Added [PULL_REQUESTS.md](PULL_REQUESTS.md) documenting planned PRs
  - Added [CHANGELOG.md](CHANGELOG.md) this file

### Changed
- **API Response Format**: Analysis reports now exclude full source code for privacy
  - Replaced `source_code` with `source_code_hash`
  - Added `source_code_lines` field for reference
  - Reduces response payload by ~95% for large contracts

### Fixed
- **Critical**: Fixed `ModuleNotFoundError` for missing `GasAnalyzer` module
- **High**: Fixed file upload UTF-8 decoding errors returning 500 instead of 400
- **High**: Added missing input validation to prevent DOS attacks
- **Medium**: Improved error messages for invalid inputs

### Security
- Added file size validation to prevent DOS
- Added file type validation to prevent processing non-Solidity files
- Improved error handling to prevent information leakage
- Removed sensitive source code from responses

### Performance
- Reduced response payload size by ~95% for large contracts
- Optimized error handling to fail fast on invalid inputs

## [1.0.0] - 2026-03-27

### Added
- Initial release of Smart Contract Auditor
- Static analysis engine for vulnerability detection
- ML-based vulnerability classification
- Explainability engine for finding explanations
- Report generation with severity scoring
- FastAPI REST endpoints
- React frontend UI
- Docker deployment support
- Test suite with 45+ tests
- Support for Solidity smart contract analysis

### Features
- Detects 15+ vulnerability types (SWC Registry)
- Reentrancy detection
- Integer overflow/underflow detection
- Unchecked return value detection
- Unprotected ether withdrawal detection
- Authorization vulnerabilities
- Floating pragma detection
- Deprecated function detection
- Gas optimization suggestions
- Risk scoring and severity classification

## Planned

### [1.2.0] - TBD
- Rate limiting per IP address
- Structured logging for audit trails
- Request/response logging
- Performance metrics collection
- Caching for repeated analyses
- WebSocket support for real-time analysis

### [1.3.0] - TBD
- Integration with GitHub for automated PR analysis
- Batch analysis improvements
- Custom rule configuration
- Plugin system for extensibility
- Database backend (MongoDB/PostgreSQL)
- Multi-contract project analysis

### [2.0.0] - TBD
- Advanced symbolic execution
- Formal verification integration
- Yul assembly analysis
- Cross-contract analysis
- Inheritance hierarchy analysis
- Storage layout analysis
- Transaction ordering analysis

## Guidelines

### Versioning

We use Semantic Versioning:
- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible feature additions
- **PATCH** version for backward-compatible bug fixes

### Categories

Changes should be categorized as:
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Now removed features
- **Fixed**: Any bug fixes
- **Security**: In case of vulnerabilities

### Release Process

1. Update version in `backend/app/main.py`
2. Update [CHANGELOG.md](CHANGELOG.md)
3. Create release branch: `release/v1.x.x`
4. Merge to main and tag: `v1.x.x`
5. Create GitHub release with notes
6. Update documentation

## Contributing

When making changes, update this file following the format above.
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
