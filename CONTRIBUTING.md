# Contributing to DarkReconX

Thank you for your interest in contributing to DarkReconX! This document provides guidelines and instructions for contributing code, tests, and documentation.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Standards](#code-standards)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Adding New Modules](#adding-new-modules)

## Code of Conduct

Be respectful, inclusive, and professional. We're building a tool for security researchers and DevSecOps professionals.

## Getting Started

### Prerequisites

- Python 3.11+
- pip
- virtualenv (recommended)
- git

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/GeoAziz/DarkReconX.git
   cd DarkReconX
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode:**
   ```bash
   make install-dev
   ```

4. **Copy environment template (optional):**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your API keys for local testing
   ```

5. **Install pre-commit hooks:**
   ```bash
   make pre-commit-install
   ```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test improvements
- `chore/description` - Maintenance and tooling

### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, commit incrementally:
   ```bash
   git add <files>
   git commit -m "Brief description of change"
   ```

3. Keep commits atomic and meaningful (see [Commit Messages](#commit-messages))

### Code Quality Checks

Before pushing, run:

```bash
# Format code
make fmt

# Run linter
make lint

# Run type checker
make type-check

# Run tests
make test
```

Or run the full CI pipeline:
```bash
make ci
```

## Testing

### Unit Tests (Offline)

Run tests that use only mocks and no network:

```bash
make test
```

Tests use `pytest` with fixtures for mocking HTTP and DNS calls. This ensures:
- No external dependencies during testing
- Deterministic results
- Fast execution
- Safe parallel test runs

### Test Coverage

Generate coverage report:

```bash
make test-cov
```

Coverage reports are generated in `htmlcov/` directory. Aim for:
- Core modules: 80%+ coverage
- New features: 100% coverage
- Integration helpers: 60%+ coverage (some integration code is hard to test)

### Integration Tests (Networked)

To run integration tests that call real APIs:

```bash
make test-integration
```

Requires:
- API keys in `.env.local` or as environment variables
- Network access
- Valid API credentials

⚠️ **Note:** Integration tests are marked with `@pytest.mark.integration` and are skipped in CI unless running on the main branch with configured secrets.

### Writing Tests

Example test structure:

```python
import pytest
from unittest.mock import MagicMock, patch

def test_my_feature():
    """Test description - what this test validates."""
    # Arrange
    expected = "result"
    mock_api = MagicMock(return_value="result")
    
    # Act
    with patch("module.api_call", mock_api):
        result = my_function()
    
    # Assert
    assert result == expected
    mock_api.assert_called_once()
```

See `tests/` directory for examples.

## Code Standards

### Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these tools enforcing standards:

- **Black** - Code formatting (line length: 127)
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Type checking (optional)

### Type Hints

Use type hints for all public functions and classes:

```python
from typing import Optional, List, Dict

def process_domain(domain: str, api_key: Optional[str] = None) -> Dict[str, str]:
    """Process a domain and return normalized results.
    
    Args:
        domain: Domain to process
        api_key: Optional API key for enrichment
        
    Returns:
        Dictionary with normalized provider data
    """
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def enrich_with_provider(domain: str, api_key: str) -> Dict:
    """Query provider API and normalize results.
    
    This function handles API calls, caching, and error handling.
    
    Args:
        domain: Domain to enrich
        api_key: API authentication key
        
    Returns:
        Dict with keys: provider, hostname, ip, asn, registrar, location, raw
    """
```

## Commit Messages

Use clear, descriptive commit messages:

```
<type>: <subject>

<body>

<footer>
```

### Type

- `feat:` - New feature
- `fix:` - Bug fix
- `test:` - Test additions or changes
- `docs:` - Documentation updates
- `style:` - Code style (formatting, missing semicolons, etc.)
- `refactor:` - Code refactoring without feature/bug changes
- `chore:` - Build process, dependencies, tooling

### Subject

- Use imperative mood ("add feature" not "added feature")
- Don't capitalize first letter
- No period at the end
- Limit to 50 characters

### Example

```
feat: add async HTTP verification to subdomain finder

- Implement httpx.AsyncClient for concurrent HTTP checks
- Add verify_http and http_timeout parameters to AsyncSubdomainFinder
- Support both HTTPS and HTTP with automatic fallback

Closes #42
```

## Pull Requests

### Before Creating a PR

1. Ensure all tests pass: `make test`
2. Ensure code is formatted: `make fmt`
3. Ensure linter passes: `make lint`
4. Write/update tests for your changes
5. Update documentation if needed

### CI Requirements

All PRs must pass:

- ✅ **Lint** - Black, isort, flake8
- ✅ **Unit Tests** - All tests pass offline
- ✅ **Type Check** - mypy validation

Integration tests run only on main branch with configured secrets.

## Adding New Modules

See [CONTRIBUTING_MODULES.md](CONTRIBUTING_MODULES.md) for detailed instructions on creating new scanner modules that integrate with DarkReconX.

## License

By contributing, you agree that your contributions will be licensed under the same license as DarkReconX (MIT).

Thank you for making DarkReconX better! 🚀
