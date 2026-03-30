# Code Quality Tools Setup Guide

This guide explains how to use the code quality tools that have been set up for this project.

## Tools Installed

1. **Ruff** - Fast Python linter and formatter (replaces flake8, isort, black)
2. **Mypy** - Static type checker
3. **isort** - Import sorter (optional, ruff can handle this too)
4. **Pre-commit** - Git hooks for automatic checks (optional)

---

## Quick Start

### 1. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Run Code Quality Checks

```bash
# Check all code quality issues
./scripts/check_code_quality.sh

# Or run individually:
ruff check .
ruff format --check .
mypy .
isort --check-only .
```

### 3. Auto-fix Issues

```bash
# Automatically fix issues where possible
./scripts/fix_code_quality.sh

# Or run individually:
ruff check --fix .
ruff format .
isort .
```

---

## Tool Configurations

### Ruff Configuration (`pyproject.toml`)

Ruff is configured to:
- Target Python 3.9+
- Use 100 character line length
- Enable comprehensive linting rules
- Exclude backup directories and build artifacts
- Auto-fix issues where possible

**Key Rules Enabled:**
- `E`, `W` - pycodestyle errors and warnings
- `F` - pyflakes (unused imports, undefined names)
- `I` - isort (import organization)
- `B` - flake8-bugbear (common bugs)
- `C4` - flake8-comprehensions
- `UP` - pyupgrade (modernize Python syntax)
- `ARG` - unused arguments
- `SIM` - simplify code

### Mypy Configuration (`pyproject.toml`)

Mypy is configured to:
- Target Python 3.9
- Warn on common type issues
- Ignore missing imports for third-party libraries
- Exclude backup directories and scripts

**Key Settings:**
- `warn_return_any` - Warn when functions return `Any`
- `warn_unused_ignores` - Warn about unnecessary `# type: ignore`
- `warn_no_return` - Warn about missing return statements
- `strict_equality` - Warn about comparing incompatible types

### isort Configuration (`.isort.cfg` and `pyproject.toml`)

isort is configured to:
- Use black-compatible profile
- Organize imports: stdlib → third-party → first-party
- Use parentheses for multi-line imports
- Exclude backup directories

---

## Usage Examples

### Check Code Quality Before Committing

```bash
# Run all checks
./scripts/check_code_quality.sh

# If issues found, auto-fix them
./scripts/fix_code_quality.sh

# Verify fixes
./scripts/check_code_quality.sh
```

### Check Specific Files

```bash
# Check a single file
ruff check app.py
mypy app.py

# Check a directory
ruff check config.py utils.py
```

### Format Code

```bash
# Format all Python files
ruff format .

# Format specific files
ruff format app.py config.py
```

### Type Check Specific Modules

```bash
# Type check core modules
mypy config.py utils.py evidence_models.py

# Type check with more verbose output
mypy app.py --show-error-codes
```

---

## Pre-commit Hooks (Optional)

Pre-commit hooks automatically run checks before each commit.

### Setup

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files
```

### What It Does

The pre-commit hooks will:
1. Run ruff linter and formatter
2. Run mypy type checker
3. Run isort import organizer

If any check fails, the commit will be blocked until issues are fixed.

---

## Integration with CI/CD

You can integrate these checks into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements-dev.txt
      - run: ./scripts/check_code_quality.sh
```

---

## Common Issues and Solutions

### Issue: "ruff: command not found"

**Solution:** Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Issue: "mypy: command not found"

**Solution:** Install mypy:
```bash
pip install mypy
```

### Issue: Type errors from third-party libraries

**Solution:** These are expected. Mypy is configured to ignore missing imports for third-party libraries. You can add specific ignores in `pyproject.toml` if needed.

### Issue: Ruff wants to change too much code

**Solution:** Review the changes carefully. Ruff's auto-fixes are generally safe, but you can:
- Review changes with `ruff check --diff .`
- Apply fixes incrementally: `ruff check --fix app.py` (one file at a time)
- Disable specific rules in `pyproject.toml` if needed

---

## Benefits

Using these tools provides:

1. **Consistency** - All code follows the same style
2. **Early Bug Detection** - Catch errors before runtime
3. **Better Type Safety** - Mypy catches type-related bugs
4. **Cleaner Code** - Automatic formatting and import organization
5. **Faster Reviews** - Automated checks reduce manual review time

---

## Future Enhancements

Consider adding:

- **Coverage.py** - Code coverage reporting
- **pytest** - More comprehensive testing framework
- **black** - Alternative formatter (ruff can replace this)
- **pylint** - Additional linting (ruff covers most cases)

---

## Questions?

If you have questions about these tools or their configuration, refer to:
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
