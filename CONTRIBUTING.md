# Contributing to Crypto-Trading-MCP

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Pull Request Process

1. **Create a Feature Branch**: Always create a new branch from `main` for your changes
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow Code Standards**:
   - Use [Black](https://black.readthedocs.io/) for code formatting
   - Use [isort](https://pycqa.github.io/isort/) for import sorting
   - Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
   - Add type hints where appropriate

3. **Write Tests**:
   - Write unit tests for new functionality
   - Maintain or improve code coverage
   - Test edge cases and error conditions

4. **Update Documentation**:
   - Update docstrings for new/changed functions
   - Update README if needed
   - Add examples for new features

5. **Commit Message Format**:
   ```
   type(scope): description

   [optional body]

   [optional footer]
   ```
   Types: `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`

## Setting Up Development Environment

1. **Clone and Setup**:
   ```bash
   git clone https://github.com/yourusername/crypto-trading-mcp.git
   cd crypto-trading-mcp
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Pre-commit Hooks** (recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Style Guidelines

- **Line Length**: 88 characters (Black default)
- **Imports**: Use absolute imports, sort with isort
- **Docstrings**: Use Google-style docstrings
- **Type Hints**: Use type hints for function parameters and return values
- **Error Handling**: Use specific exception types, include helpful error messages

### Example Code Style:
```python
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def process_market_data(
    symbol: str,
    data: Dict[str, float],
    validation: bool = True
) -> Optional[List[Dict[str, float]]]:
    """Process market data for a given trading symbol.

    Args:
        symbol: Trading symbol (e.g., 'BTC-USD')
        data: Market data dictionary containing price information
        validation: Whether to validate data before processing

    Returns:
        Processed market data or None if invalid

    Raises:
        ValueError: If symbol format is invalid
        DataProcessingError: If data processing fails
    """
    if not symbol or not symbol.replace('-', '').replace('_', '').isalnum():
        raise ValueError(f"Invalid symbol format: {symbol}")

    try:
        # Processing logic here
        return processed_data
    except Exception as e:
        logger.error(f"Failed to process data for {symbol}: {e}")
        raise DataProcessingError(f"Processing failed: {e}") from e
```

## Testing Guidelines

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **Test Coverage**: Aim for 80%+ coverage
- **Mock External Services**: Use mocks for API calls and external dependencies

### Running Tests:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_trading.py

# Run with verbose output
pytest -v
```

## Security Guidelines

- **Never commit secrets**: API keys, passwords, tokens
- **Use environment variables**: For sensitive configuration
- **Validate inputs**: Sanitize all external inputs
- **Follow security best practices**: OWASP guidelines
- **Regular dependency updates**: Keep dependencies current

## Issue Reporting

When reporting issues:

1. **Use issue templates**: Bug report or feature request templates
2. **Provide context**: Operating system, Python version, error logs
3. **Minimal reproduction**: Smallest code example that reproduces the issue
4. **Expected vs actual behavior**: Clear description of what went wrong

## Feature Requests

For new features:

1. **Check existing issues**: Avoid duplicates
2. **Describe the use case**: Why is this feature needed?
3. **Propose solution**: How should it work?
4. **Consider alternatives**: Other approaches you've considered

## Code Review Process

All submissions go through code review:

1. **Automated checks**: CI/CD pipeline runs tests and linting
2. **Peer review**: At least one maintainer reviews the code
3. **Discussion**: Address feedback and make requested changes
4. **Approval**: Code is merged after approval

## Getting Help

- **Documentation**: Check the README and docs/ directory
- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for general questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Recognition

Contributors will be recognized in the project's contributors list and release notes.

Thank you for contributing to Crypto-Trading-MCP! 🚀