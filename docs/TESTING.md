# Testing Guide — DocGen

## 1. Quick Start

```bash
# Install the package + all dev dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest

# Run with coverage report
pytest --cov=src/autodocstring --cov-report=term-missing
```

`[dev]` extras include: `pytest`, `pytest-cov`, `black`, `mypy`, `flake8`, `httpx`.

---

## 2. Test Structure

```
tests/
├── __init__.py
├── conftest.py             # Shared fixtures (sample files, temp dirs, mock providers)
├── test_api.py             # FastAPI endpoint integration tests
├── test_confidence.py      # ConfidenceScorer unit tests
├── test_generator.py       # DocstringGenerator + HybridDocstringEngine tests
├── test_parser.py          # AST parser + extractor tests
├── test_safety.py          # SafeApplier behaviour tests
├── test_validation.py      # Style checker tests
├── fixtures/               # Static input files for tests
└── sample_project/         # Multi-file Python project used in integration tests
    ├── calc.py
    ├── math_utils.py
    ├── string_utils.py
    ├── syntax_error.py     # Intentionally broken file (tests error handling)
    ├── api/
    ├── async_ops/
    ├── core/
    ├── data/
    ├── decorators/
    ├── hard_cases/
    ├── legacy/
    └── utils/
```

---

## 3. What is Tested

### `test_parser.py`

Tests `ast_parser.py` and `extractors.py`:

- Extracts class names, method names, function names
- Correctly identifies parameter names, type hints, defaults, and `*args`/`**kwargs`
- Detects `async def` functions
- Detects decorators (`@staticmethod`, `@classmethod`, `@property`)
- Returns module-level docstring when present
- Handles files with syntax errors gracefully (returns empty metadata, not an exception)

### `test_confidence.py`

Tests `ConfidenceScorer`:

- Fully annotated function scores ≥ 0.85 (`AUTO_APPLY`)
- Adding untyped parameters decreases score by 0.05 each
- Missing return annotation reduces score by 0.10
- Functions with branch count > 8 take a −0.10 penalty
- Generator functions (`yield`) take a −0.05 penalty
- Threshold buckets are correctly assigned (`AUTO_APPLY`, `REVIEW`, `SKIP`)
- Whitelist of builtins (`print`, `len`, `range` …) does not trigger "external call" penalty

### `test_generator.py`

Tests both `DocstringGenerator` and `HybridDocstringEngine`:

- Google style renders `Args:`, `Returns:`, `Raises:` sections
- NumPy style renders dashed underlines under section headers
- reST style uses `:param name:` syntax
- Epytext style uses `@param name:` syntax
- Sphinx style uses `:param type name:` syntax
- Functions with no parameters omit the Args section
- Functions with no return annotation omit the Returns section
- `# autodoc: ignore` directive skips generation (returns `generation_type="skipped"`)
- `rewrite_existing=False` skips functions that already have a docstring
- `HybridDocstringEngine` falls back to template when no LLM provider configured
- Template summary placeholder is replaced when LLM provider returns a result

### `test_safety.py`

Tests `SafeApplier`:

- Applies a valid docstring and the resulting file parses without error
- Idempotent: applying the same docstring twice does not double-insert it
- Rolls back to original content when generated docstring would cause a syntax error
- Dry-run mode returns a diff without modifying the file
- `SkipRecord` is returned (not an exception) when application is skipped

### `test_api.py`

Integration tests for the FastAPI endpoints (uses `TestClient` from `httpx`):

- `GET /api/v1/health` returns `200` with `status: "healthy"`
- `POST /api/v1/scan` with a valid Python file returns coverage stats
- `POST /api/v1/generate` returns `DocstringResult` objects for undocumented functions
- `POST /api/v1/apply` writes docstrings and returns the documented content
- `POST /api/v1/undo` restores the original content
- `POST /api/v1/scan` with a file that has syntax errors returns a descriptive error response
- Session isolation: two concurrent sessions do not share file state

### `test_validation.py`

Tests the style checker:

- `is_style_match()` correctly identifies Google, NumPy, reST, Epytext, and Sphinx docstrings
- `is_complete()` returns `False` when a parameter is undocumented
- `is_complete()` returns `True` when all params and Returns are documented
- Style mismatch (e.g., Google-style docstring checked against NumPy) returns `False`

---

## 4. Fixtures (`conftest.py`)

Key fixtures available to all tests:

| Fixture | Type | Description |
|---------|------|-------------|
| `tmp_py_file(content)` | factory | Creates a temp `.py` file with given content; deleted after test |
| `sample_function_meta` | `FunctionMetadata` | A fully annotated function with 2 params and return type |
| `untyped_function_meta` | `FunctionMetadata` | Same function with no type hints |
| `mock_groq_provider` | mock | Groq provider that returns a fixed summary sentence |
| `test_client` | `TestClient` | FastAPI test client with isolated temp session dir |

---

## 5. Running Specific Tests

```bash
# Run only parser tests
pytest tests/test_parser.py -v

# Run only a specific test class
pytest tests/test_generator.py::TestHybridEngine -v

# Run only tests matching a keyword
pytest -k "confidence" -v

# Run tests and stop on first failure
pytest -x

# Run with verbose output for all tests
pytest -v

# Show slowest 5 tests
pytest --durations=5
```

---

## 6. Coverage

```bash
# Terminal report (shows missing lines)
pytest --cov=src/autodocstring --cov-report=term-missing

# HTML report (open htmlcov/index.html in a browser)
pytest --cov=src/autodocstring --cov-report=html
```

Target coverage: **≥ 80%** for all non-trivial modules. The `safety/` and `confidence/` modules are fully unit-testable and should reach ≥ 95%.

---

## 7. Type Checking & Linting

```bash
# Static type checking
mypy src/autodocstring

# Linting
flake8 src/autodocstring

# Code formatting check (does not modify files)
black --check src/autodocstring

# Auto-format
black src/autodocstring
```

---

## 8. Testing the Demo Files

The `demo/` directory contains 5 categories of Python files, useful for manual end-to-end testing:

| Folder | What it tests |
|--------|---------------|
| `01_no_docstrings/` | All functions undocumented — maximum generation coverage expected |
| `02_partial_docstrings/` | Mix of documented and undocumented — should not overwrite existing ones |
| `03_style_mismatch/` | Existing docstrings in wrong style — tests rewrite_existing logic |
| `04_complex_patterns/` | Async, algorithms, design patterns — tests confidence scoring under complexity |
| `05_edge_cases/` | Dataclasses, decorators, generators — tests parser edge cases |

Upload these through the web UI at `http://localhost:5173` or run them directly:

```bash
# Command-line scan (no web UI)
python -m autodocstring scan demo/01_no_docstrings/calculator.py --style google
```

---

## 9. Continuous Integration

Tests run automatically on GitHub Actions for every push:

- Python version: **3.11**
- Test command: `pytest --tb=short`
- Workflow file: `.github/workflows/ci.yml`

To reproduce the CI environment locally:

```bash
pip install -e ".[dev]"
pytest --tb=short
```
