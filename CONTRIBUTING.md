# Contributing to Smart Contract Auditor

Thank you for your interest in contributing to the Smart Contract Auditor project! This guide will help you get started.

## Getting Started

### Prerequisites
- Python 3.11+
- Git
- pip or conda for package management

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/code-with-harish/Contract-Auditor.git
   cd Contract-Auditor
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   pip install pytest pytest-cov black flake8
   ```

4. **Run tests to verify setup**
   ```bash
   pytest tests/
   ```

## Workflow

### Creating a Feature Branch

All new features should be developed on a feature branch:

```bash
git checkout -b feature/your-feature-name
git checkout -b bugfix/issue-number
git checkout -b docs/improvement-name
```

### Branch Naming Convention

- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test improvements

### Making Changes

1. **Make your changes** following the code style guidelines below
2. **Write tests** for new functionality
3. **Run the test suite** to ensure nothing breaks
4. **Format your code** with black

   ```bash
   black backend/
   ```

5. **Check code quality** with flake8
   ```bash
   flake8 backend/
   ```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (formatting, missing semicolons, etc)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Test updates

#### Examples

**Good:**
```
feat(analyzer): Add gas optimization detection

- Implement GasAnalyzer class
- Add 7 optimization rules
- Calculate efficiency score

Fixes #1
```

**Good:**
```
fix(api): Add error handling for UTF-8 decoding

Wrap file decode in try/except to return 400 errors
instead of 500 errors. Return descriptive message.

Fixes #2
```

**Good:**
```
docs: Add contributing guide

Provide guidelines for setup, workflow, and PR requirements.
```

### Pushing and Creating a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:

1. **Clear title** that summarizes the change
2. **Description** explaining:
   - What problem does this solve?
   - How does it solve the problem?
   - Any breaking changes?
3. **Linked issues** - Reference relevant issues with `Fixes #123`
4. **Checklist** - Verify tests pass, docs updated, etc.

## Code Style Guidelines

### Python Code

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints where possible
- Maximum line length: 100 characters
- Use meaningful variable names
- Add docstrings to functions and classes

**Example:**
```python
def analyze_contract(source_code: str) -> Dict[str, Any]:
    """
    Analyze a Solidity contract for vulnerabilities.
    
    Args:
        source_code: The Solidity contract source code
        
    Returns:
        Dictionary containing analysis results
    """
    findings = []
    # implementation
    return findings
```

### Commit Messages

- Use imperative mood ("add feature" not "added feature")
- Be specific about what changed
- Keep first line under 50 characters
- Reference issues when applicable

## Testing

### Writing Tests

Create tests in `tests/test_*.py` files. Use pytest:

```python
def test_feature_works():
    """Test description."""
    # Arrange
    input_data = "test"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_output
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend tests/

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

### Test Coverage

Aim for at least 80% code coverage on new features.

## Documentation

- Update [README.md](README.md) for user-facing changes
- Update [ISSUES.md](ISSUES.md) when creating tracked issues
- Update [PULL_REQUESTS.md](PULL_REQUESTS.md) for major PRs
- Add docstrings to all public functions and classes
- Add comments for complex logic

## API Documentation

The API uses FastAPI. Documentation is auto-generated and available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Performance Considerations

When optimizing, consider:
- Memory usage (especially for large contracts)
- Analysis time (keep under 5 seconds per contract)
- Response payload size
- Database query efficiency

## Security Considerations

- Never commit secrets or API keys
- Validate all user inputs
- Use parameterized queries if using SQL
- Follow OWASP security best practices
- Run security checks on dependencies

## Getting Help

- Check [ISSUES.md](ISSUES.md) for known issues
- Review existing PRs for similar changes
- Open a discussion issue for questions
- Join our community (if applicable)

## Review Process

All PRs require:

- [ ] Tests pass (`pytest`)
- [ ] Code is formatted (`black`)
- [ ] Code quality checks pass (`flake8`)
- [ ] Documentation is updated
- [ ] At least one approving review
- [ ] No merge conflicts

## Recognition

Contributors will be recognized in:
- [README.md](README.md) contributors section
- GitHub contributors page
- Release notes for major contributions

Thank you for contributing to Smart Contract Auditor! 🙏
