# pytest Framework Skeleton

[![Tests](https://github.com/tshimbo/pytest-framework-skeleton/actions/workflows/test.yml/badge.svg)](https://github.com/tshimbo/pytest-framework-skeleton/actions/workflows/test.yml)
[![Security](https://github.com/tshimbo/pytest-framework-skeleton/actions/workflows/security.yml/badge.svg)](https://github.com/tshimbo/pytest-framework-skeleton/actions/workflows/security.yml)
![License](https://img.shields.io/badge/license-MIT-green)

> A reusable pytest project with shared fixtures, conftest hierarchy, parametrize, HTML/JSON reporting, and GitHub Actions CI. Built as **Project 1** of the SET (Software Engineer in Test) preparation roadmap.

---

## Project Structure

```
pytest-framework-skeleton/
├── src/
│   ├── models/
│   │   └── order.py              # Order dataclass (symbol, side, qty, price)
│   └── validators/
│       └── order_validator.py    # Validation logic with typed errors
├── tests/
│   ├── conftest.py               # Root fixtures (session, module, function scope)
│   ├── unit/
│   │   ├── conftest.py           # Unit-specific fixtures
│   │   ├── test_order_model.py   # Order model tests
│   │   └── test_order_validator.py  # Parametrized validator tests
│   └── integration/
│       ├── conftest.py           # HTTP server fixture (module-scoped)
│       └── test_order_submission.py  # End-to-end HTTP submission tests
├── .github/workflows/test.yml    # CI pipeline
├── Makefile                      # Developer commands
├── pyproject.toml                # Project config, pytest markers, mypy, coverage
├── requirements.txt              # Pinned dependencies
└── README.md
```

## Quick Start

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
make install

# Run all tests
make test

# Run smoke tests only (fast)
make smoke
```

## Available Make Targets

| Command          | Description                                  |
|------------------|----------------------------------------------|
| `make test`      | Run all tests with verbose output            |
| `make smoke`     | Run smoke tests only                         |
| `make regression`| Run regression tests                         |
| `make unit`      | Run unit tests only                          |
| `make integration`| Run integration tests only                  |
| `make cov`       | Run tests with coverage (fail if < 80%)      |
| `make report`    | Generate HTML + JSON test reports            |
| `make lint`      | Run flake8 linter                            |
| `make typecheck` | Run mypy type checker                        |
| `make parallel`  | Run tests in parallel (pytest-xdist)         |
| `make ci`        | Full local CI: lint → typecheck → cov → report |
| `make clean`     | Remove all generated artifacts               |

## Key Concepts Demonstrated

### Conftest Hierarchy
- **`tests/conftest.py`** — Root fixtures available everywhere: `sample_buy_order`, `sample_sell_order`, `make_order` factory, `db_connection` (session-scoped)
- **`tests/unit/conftest.py`** — Unit-specific: `cancelled_order`, `bulk_orders`
- **`tests/integration/conftest.py`** — Integration-specific: `http_server` (module-scoped, spins up a real HTTP server)

### Fixture Scopes
- **session** — `db_connection`, `test_session_id` (created once per run)
- **module** — `http_server`, `order_book` (created once per test file)
- **function** — All order fixtures (fresh for each test)

### Custom Marks
- `@pytest.mark.smoke` — Quick sanity checks
- `@pytest.mark.regression` — Guards against known bugs
- `@pytest.mark.slow` — Long-running tests (deselect with `-m "not slow"`)
- `@pytest.mark.integration` — Tests requiring external resources

### Parametrize
See `test_order_validator.py` — 5 validation cases in a single test function with descriptive IDs.

## How to Extend

### Adding a new fixture
1. Decide the scope (session/module/function) and audience (all tests vs. unit vs. integration)
2. Add the fixture to the appropriate `conftest.py`
3. Use it by name in any test function parameter list

### Adding a parametrized test
```python
@pytest.mark.parametrize("input,expected", [
    ("AAPL", True),
    ("FAKE", False),
], ids=["valid_symbol", "invalid_symbol"])
def test_symbol_lookup(input, expected):
    assert is_valid_symbol(input) == expected
```

### Adding a new test module
1. Create the file in the appropriate directory (`tests/unit/` or `tests/integration/`)
2. Name it `test_*.py`
3. Import fixtures by parameter name — no manual imports needed

## CI Pipeline

On every push and PR, across Python 3.11, 3.12, and 3.13 (29 tests, 98% coverage, warnings treated as errors):
1. **Lint** — flake8 with 120 char line limit
2. **Type check** — mypy strict mode
3. **Tests + Coverage** — Fails if coverage drops below 80%
4. **Reports** — HTML + JSON uploaded as artifacts

Matrix tested on Python 3.11 and 3.12.

---

*Built as part of the SET Preparation Roadmap — Phase 1, Project 1.*

## License
MIT
