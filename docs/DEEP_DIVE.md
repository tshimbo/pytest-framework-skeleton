# Project 1: pytest Framework Skeleton — Complete Deep Dive

> Everything you need to understand about this project, line by line.

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Project Structure Map](#2-project-structure-map)
3. [The Order Model (`src/models/order.py`)](#3-the-order-model)
4. [The Validator (`src/validators/order_validator.py`)](#4-the-validator)
5. [Conftest Hierarchy — The Heart of pytest](#5-conftest-hierarchy)
6. [Fixture Scopes — session vs module vs function](#6-fixture-scopes)
7. [The Factory Fixture Pattern](#7-the-factory-fixture-pattern)
8. [Unit Tests Explained](#8-unit-tests-explained)
9. [Parametrize — One Test, Many Cases](#9-parametrize)
10. [Custom Marks — smoke, regression, slow](#10-custom-marks)
11. [Integration Tests — Real HTTP Server](#11-integration-tests)
12. [pytest Hooks — Customising Behaviour](#12-pytest-hooks)
13. [The Makefile — Developer Experience](#13-the-makefile)
14. [pyproject.toml — Configuration Central](#14-pyprojecttoml)
15. [GitHub Actions CI Pipeline](#15-github-actions-ci)
16. [How pytest Discovers and Runs Tests](#16-how-pytest-works)
17. [Interview Questions This Prepares You For](#17-interview-questions)

---

## 1. What This Project Is

This is a **reusable pytest testing framework** built to demonstrate the core skills a Software Engineer in Test (SET) needs. It's not a toy — it models a real-world scenario (validating trading orders) and uses the exact same patterns you'd see in a production test suite at a trading firm.

**What it does:**
- Defines an `Order` model (like a trading order: "Buy 100 AAPL at $150")
- Validates orders (reject invalid symbol, zero quantity, negative price, etc.)
- Tests everything with pytest using professional patterns
- Runs in CI with coverage gates and HTML reports

**Why this matters for Citadel Securities:**
- The SET role requires building test frameworks from scratch
- Interviewers probe deeply on pytest fixtures, conftest, and CI design
- This project gives you concrete answers to "walk me through your test framework"

---

## 2. Project Structure Map

```
pytest-framework-skeleton/
│
├── src/                          # APPLICATION CODE (what we're testing)
│   ├── __init__.py               # Makes src/ a Python package
│   ├── models/
│   │   ├── __init__.py
│   │   └── order.py              # ⭐ The Order dataclass + enums
│   └── validators/
│       ├── __init__.py
│       └── order_validator.py    # ⭐ Validation logic + custom exception
│
├── tests/                        # TEST CODE
│   ├── __init__.py
│   ├── conftest.py               # ⭐ ROOT conftest — fixtures for ALL tests
│   ├── unit/                     # Unit tests (no I/O, no servers)
│   │   ├── __init__.py
│   │   ├── conftest.py           # ⭐ Unit-specific fixtures
│   │   ├── test_order_model.py   # Tests for the Order dataclass
│   │   └── test_order_validator.py # ⭐ Parametrized validation tests
│   └── integration/              # Integration tests (real servers, real I/O)
│       ├── __init__.py
│       ├── conftest.py           # ⭐ HTTP server fixture
│       └── test_order_submission.py # Tests POSTing orders to live server
│
├── .github/workflows/test.yml    # ⭐ CI pipeline definition
├── Makefile                      # Developer command shortcuts
├── pyproject.toml                # Project + tool configuration
├── requirements.txt              # Pinned dependencies
└── README.md                     # User-facing documentation
```

**Rule of thumb:** `src/` = what the production code does. `tests/` = proving it works.

---

## 3. The Order Model

**File:** `src/models/order.py`

### What is a dataclass?

A `@dataclass` is Python's way of saying "this class is just a container for data." It automatically generates:

| Generated Method | What It Does |
|---|---|
| `__init__()` | Constructor — `Order(symbol="AAPL", side=Side.BUY, ...)` |
| `__repr__()` | Pretty printing — `Order(symbol='AAPL', side=<Side.BUY>, ...)` |
| `__eq__()` | Equality — two Orders with same fields are `==` |

Without `@dataclass`, you'd write 30+ lines of boilerplate.

### What are Enums and why use them?

```python
class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"
```

An Enum restricts a field to a **fixed set of values**. This prevents bugs:

| Code | Result |
|---|---|
| `order.side = Side.BUY` | ✅ Valid |
| `order.side = "BUY"` | ⚠️ Type checker warns |
| `order.side = Side.BANANA` | ❌ AttributeError at runtime |
| `order.side = "banana"` | ⚠️ Type checker warns, might cause silent bugs |

Without Enums, a typo like `"BUUY"` would pass silently and cause downstream failures.

### The field(default_factory=...) pattern

```python
order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

**Why not just `order_id: str = str(uuid.uuid4())`?**

Because default values are evaluated **once at class definition time**. Every Order would get the **same** UUID! `default_factory` ensures the lambda runs **fresh for each instance**.

| Approach | Result |
|---|---|
| `order_id = str(uuid.uuid4())` | ❌ All orders share the same ID |
| `order_id = field(default_factory=...)` | ✅ Each order gets a unique ID |

### @property methods

```python
@property
def remaining_quantity(self) -> int:
    return self.quantity - self.filled_quantity
```

`@property` makes a method act like an attribute. You access it as `order.remaining_quantity` (no parentheses), not `order.remaining_quantity()`. It recomputes every time you access it.

### The Order Lifecycle

```
   ┌─────────┐
   │   NEW   │  ← Order is created
   └────┬────┘
        │
   ┌────▼─────────────┐
   │ PARTIALLY_FILLED  │  ← Some shares filled, some remain
   └────┬─────────────┘
        │
   ┌────▼────┐     ┌───────────┐     ┌──────────┐
   │  FILLED │     │ CANCELLED │     │ REJECTED │
   └─────────┘     └───────────┘     └──────────┘
    Terminal         Terminal          Terminal
```

`is_complete` returns `True` for the three terminal states.

---

## 4. The Validator

**File:** `src/validators/order_validator.py`

### Custom Exception with field tracking

```python
class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
```

**Why not just use `ValueError`?**

Because our exception carries **structured data**:
- `exc.field` = which field failed (`"symbol"`, `"quantity"`, `"price"`)
- `exc.message` = human-readable description

This lets tests be precise:
```python
with pytest.raises(ValidationError) as exc_info:
    validate_order(bad_order)
assert exc_info.value.field == "quantity"  # We know EXACTLY what failed
```

With a plain `ValueError`, you'd have to match on the message string — brittle!

### Guard clause pattern

```python
def _validate_symbol(symbol):
    if not symbol:                    # Guard 1: empty?
        raise ValidationError(...)
    if symbol not in VALID_SYMBOLS:   # Guard 2: unknown?
        raise ValidationError(...)
    # If we get here, it's valid (implicit return None)
```

Guard clauses check bad cases first and `raise` immediately. This keeps the code flat — no deeply nested `if/elif/else` blocks.

### Why a Set for VALID_SYMBOLS?

```python
VALID_SYMBOLS = {"AAPL", "GOOGL", ...}  # This is a SET, not a list
```

| Data Structure | `"AAPL" in x` time | Why |
|---|---|---|
| `set` | O(1) constant | Hash table lookup |
| `list` | O(n) linear | Checks every element |

For 16 symbols it doesn't matter. For 10,000 symbols on a real exchange, sets are **essential**.

---

## 5. Conftest Hierarchy — The Heart of pytest

### What is conftest.py?

`conftest.py` is a **magic filename** that pytest automatically discovers. Any fixture defined in it is automatically available to tests — no imports needed.

### How the hierarchy works

```
tests/
├── conftest.py              ← Level 0: Available to ALL tests
├── unit/
│   ├── conftest.py          ← Level 1: Available to tests/unit/** ONLY
│   └── test_order_model.py
└── integration/
    ├── conftest.py          ← Level 1: Available to tests/integration/** ONLY
    └── test_order_submission.py
```

When `test_order_model.py` asks for a fixture, pytest searches:
1. The test file itself
2. `tests/unit/conftest.py` (closest conftest)
3. `tests/conftest.py` (parent conftest)
4. Installed plugins

**The first match wins.** This lets child conftest files override parent ones.

### What lives where

| Conftest | Fixtures | Why here |
|---|---|---|
| `tests/conftest.py` | `sample_buy_order`, `sample_sell_order`, `make_order`, `db_connection` | Needed by both unit AND integration tests |
| `tests/unit/conftest.py` | `cancelled_order`, `bulk_orders` | Only unit tests need these |
| `tests/integration/conftest.py` | `http_server` | Only integration tests need a live server |

---

## 6. Fixture Scopes

### The four scopes

| Scope | Lifetime | Created | Destroyed | Use for |
|---|---|---|---|---|
| `session` | Entire test run | Once, ever | After last test | DB connections, Docker containers |
| `module` | One test file | Once per file | After last test in file | HTTP servers, file handles |
| `class` | One test class | Once per class | After last method | Shared class state |
| `function` | One test | Every test | After each test | Mutable objects (orders, counters) |

### The tradeoff

```
← Broader scope = FASTER (less setup/teardown) ──────────────────────→
← Narrower scope = SAFER (no shared mutable state between tests) ───→

session ◄──────► module ◄──────► class ◄──────► function
```

### Yield fixtures (setup/teardown)

```python
@pytest.fixture(scope="session")
def db_connection():
    conn = connect()       # ← SETUP: runs before first test using this fixture
    yield conn             # ← TEST RUNS HERE (conn is passed to the test)
    conn.close()           # ← TEARDOWN: runs after last test, even if tests fail!
```

The code **after** `yield` is guaranteed to run — it's like a `finally` block.

---

## 7. The Factory Fixture Pattern

```python
@pytest.fixture
def make_order():
    def _make_order(**kwargs) -> Order:
        defaults = {"symbol": "AAPL", "side": Side.BUY, "quantity": 100, ...}
        defaults.update(kwargs)       # Override only the fields you specify
        return Order(**defaults)
    return _make_order                # Return the FUNCTION, not an order
```

### Why use a factory?

| Need | Regular Fixture | Factory Fixture |
|---|---|---|
| One specific order | ✅ `sample_buy_order` | `make_order()` |
| Order with custom symbol | ❌ Need a new fixture | ✅ `make_order(symbol="TSLA")` |
| 10 diverse orders | ❌ Need 10 fixtures | ✅ Loop: `make_order(symbol=s)` |
| Order with only qty changed | ❌ Copy-paste fixture | ✅ `make_order(quantity=500)` |

A factory gives you **infinite flexibility** with one fixture.

---

## 8. Unit Tests Explained

**File:** `tests/unit/test_order_model.py`

### Test class structure

```python
class TestOrderCreation:        # Tests for creating orders
class TestOrderProperties:      # Tests for computed properties
class TestOrderFactory:         # Tests for the factory fixture
class TestSessionScopedFixture: # Tests proving session scope works
```

Classes group related tests. In CI output:
```
TestOrderCreation::test_buy_order_has_correct_side         PASSED
TestOrderCreation::test_sell_order_has_correct_symbol      PASSED
TestOrderProperties::test_remaining_quantity_new_order     PASSED
```

### Fixture injection

```python
def test_buy_order_has_correct_side(self, sample_buy_order: Order) -> None:
    assert sample_buy_order.side == Side.BUY
```

The test **never imports conftest.py**. It just names `sample_buy_order` in its parameter list. pytest:
1. Sees the parameter name
2. Looks it up in the fixture registry
3. Calls the fixture function
4. Passes the return value to the test

This is called **dependency injection**.

### Assertions

```python
assert sample_buy_order.side == Side.BUY
```

If this fails, pytest shows a **rich diff**:
```
AssertionError: assert <Side.SELL: 'SELL'> == <Side.BUY: 'BUY'>
```

No need for `assertEqual`, `assertTrue`, etc. — plain `assert` gives you everything.

---

## 9. Parametrize — One Test, Many Cases

**File:** `tests/unit/test_order_validator.py`

```python
@pytest.mark.parametrize(
    "symbol, side, qty, price, order_type, expected_error_field",
    [
        ("AAPL", Side.BUY, 100, 150.0, OrderType.LIMIT, None),        # Valid
        ("AAPL", Side.BUY, 0, 150.0, OrderType.LIMIT, "quantity"),     # Zero qty
        ("AAPL", Side.SELL, 100, -10.0, OrderType.LIMIT, "price"),     # Neg price
        ("", Side.BUY, 100, 150.0, OrderType.LIMIT, "symbol"),         # Empty symbol
        ("MSFT", Side.BUY, 2_000_000, 300.0, OrderType.LIMIT, "quantity"),  # Fat finger
    ],
    ids=["valid_order", "zero_quantity", "negative_price", "missing_symbol", "oversized_quantity"],
)
def test_order_validation_cases(self, symbol, side, qty, price, order_type, expected_error_field):
    ...
```

### How it works

pytest generates **5 separate test cases** from this one function:

```
test_order_validation_cases[valid_order]         PASSED
test_order_validation_cases[zero_quantity]        PASSED
test_order_validation_cases[negative_price]       PASSED
test_order_validation_cases[missing_symbol]       PASSED
test_order_validation_cases[oversized_quantity]   PASSED
```

If one fails, you see **exactly which case** failed, not just "validation test failed."

### The ids parameter

Without `ids`, pytest shows raw values:
```
test_order_validation_cases[AAPL-Side.BUY-0-150.0-OrderType.LIMIT-quantity]
```

With `ids`, you get human-readable names:
```
test_order_validation_cases[zero_quantity]
```

---

## 10. Custom Marks

```python
@pytest.mark.smoke       # Quick sanity check
@pytest.mark.regression  # Guards against known bugs
@pytest.mark.slow        # Takes longer than usual
@pytest.mark.integration # Needs external resources
```

### How to use them

| Command | What it runs | Time |
|---|---|---|
| `make smoke` | Only `@pytest.mark.smoke` tests | ~1 sec |
| `make regression` | Only `@pytest.mark.regression` tests | ~1 sec |
| `make test -m "not slow"` | Everything except slow tests | ~1 sec |
| `make integration` | Only integration tests | ~2 sec |
| `make test` | Everything | ~2 sec |

### Registration in pyproject.toml

```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "smoke: marks tests as smoke tests",
]
addopts = "--strict-markers"  # ← Typos in marks cause errors, not silent passes
```

`--strict-markers` means `@pytest.mark.smok` (typo) raises an error instead of silently creating a new mark.

---

## 11. Integration Tests

**File:** `tests/integration/test_order_submission.py`

### Architecture

```
┌──────────────┐     HTTP POST      ┌─────────────────────┐
│  Test Code   │ ──────────────────► │  HTTPServer         │
│  (pytest)    │                     │  (background thread) │
│              │ ◄────────────────── │                     │
│              │     JSON response   │  received_orders: [] │
└──────────────┘                     └─────────────────────┘
   Function scope                      Module scope
   (fresh each test)                   (shared across tests in file)
```

### The HTTP server fixture

```python
@pytest.fixture(scope="module")
def http_server():
    server = HTTPServer(("localhost", 0), OrderSubmissionHandler)  # Port 0 = random
    port = server.server_address[1]                                # Read actual port
    thread = Thread(target=server.serve_forever, daemon=True)      # Background thread
    thread.start()
    yield ("localhost", port)  # Tests run here
    server.shutdown()          # Cleanup
```

Key details:
- **Port 0**: OS picks a random available port (avoids conflicts in CI)
- **daemon=True**: Thread dies automatically if the process crashes
- **Module scope**: Server starts once per test file, not once per test

### Negative testing

```python
def test_invalid_json_returns_400(self, http_server):
    req = Request(url, data=b"not json at all", method="POST")
    try:
        urlopen(req)
        assert False, "Expected HTTP 400"  # If we get here, test FAILS
    except HTTPError as e:
        assert e.code == 400               # Server correctly rejected bad input
```

Good tests don't just verify the happy path. They verify the system handles **bad input** gracefully.

---

## 12. pytest Hooks

**File:** `tests/conftest.py` (bottom)

### pytest_runtest_logreport

```python
def pytest_runtest_logreport(report):
    if report.when == "call":
        print(f"[{timestamp}] {outcome} {report.nodeid} ({duration})")
```

This hook fires after every test phase. We filter for `when == "call"` (the actual test, not setup/teardown) and print a live log:

```
[10:30:00.123] PASSED tests/unit/test_order_model.py::TestOrderCreation::test_buy (0.001s)
[10:30:00.125] FAILED tests/unit/test_order_model.py::TestOrderCreation::test_sell (0.002s)
```

### pytest_configure

```python
def pytest_configure(config):
    config._metadata["Project"] = "pytest-framework-skeleton"
```

Runs once at startup. Adds metadata to the HTML report header.

---

## 13. The Makefile

| Target | Command | What it does |
|---|---|---|
| `make install` | `pip install -r requirements.txt -e .` | Install everything |
| `make test` | `pytest -v` | Run all tests |
| `make smoke` | `pytest -v -m smoke` | Quick sanity tests only |
| `make regression` | `pytest -v -m regression` | Regression tests only |
| `make unit` | `pytest -v tests/unit/` | Unit tests only |
| `make integration` | `pytest -v tests/integration/` | Integration tests only |
| `make cov` | `pytest --cov=src --cov-fail-under=80` | Tests + coverage gate |
| `make report` | `pytest --html=report.html --json-report` | HTML + JSON reports |
| `make lint` | `flake8 src/ tests/` | Code style check |
| `make typecheck` | `mypy src/` | Static type checking |
| `make parallel` | `pytest -n auto` | Run tests in parallel |
| `make ci` | lint → typecheck → cov → report | Full CI pipeline locally |
| `make clean` | `rm -rf ...` | Remove all generated files |

---

## 14. pyproject.toml

This single file configures **four tools**:

### pytest configuration
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]         # Where to find tests
markers = [...]               # Register custom marks
addopts = "-v --strict-markers"  # Always verbose, strict mark names
```

### mypy configuration
```toml
[tool.mypy]
disallow_untyped_defs = true  # Every function must have type hints
check_untyped_defs = true     # Type-check even without annotations
```

### Coverage configuration
```toml
[tool.coverage.run]
source = ["src"]              # Only measure src/ coverage (not tests)

[tool.coverage.report]
fail_under = 80               # CI fails if coverage drops below 80%
show_missing = true           # Show which lines aren't covered
```

---

## 15. GitHub Actions CI Pipeline

**File:** `.github/workflows/test.yml`

### Pipeline flow

```
Every push to main / Every PR
        │
        ▼
┌───────────────────────────────┐
│  Matrix: Python 3.11 + 3.12  │
│                               │
│  1. Checkout code             │
│  2. Setup Python + pip cache  │
│  3. pip install               │
│  4. make lint (flake8)        │
│  5. make typecheck (mypy)     │
│  6. make cov (fail < 80%)    │
│  7. make report (HTML+JSON)   │
│  8. Upload report artifacts   │
└───────────────────────────────┘
```

### Key details

- **Matrix strategy**: Runs on Python 3.11 AND 3.12 in parallel
- **`if: always()`**: Report generation runs even if tests fail (so you can see the report)
- **Artifact upload**: HTML report is downloadable from the GitHub Actions page
- **pip cache**: `cache: pip` speeds up subsequent runs by caching downloaded packages

---

## 16. How pytest Discovers and Runs Tests

### Discovery phase

```
pytest starts
  │
  ├─ Read pyproject.toml → testpaths = ["tests"]
  ├─ Walk tests/ directory recursively
  ├─ Find files matching test_*.py or *_test.py
  ├─ Find conftest.py files at each level
  ├─ Inside each file, find:
  │   ├─ Functions named test_*
  │   └─ Classes named Test* with methods named test_*
  └─ Expand @parametrize into individual test items
```

### Execution phase (for each test)

```
1. SETUP
   ├─ Resolve all fixture dependencies
   ├─ Create fixtures (respecting scope — session fixtures only once)
   └─ Inject fixture values as function parameters

2. CALL
   ├─ Run the test function
   └─ Record pass/fail/error

3. TEARDOWN
   ├─ Run code after yield in fixtures
   └─ Destroy function-scoped fixtures
```

---

## 17. Interview Questions This Prepares You For

| Question | Your Answer |
|---|---|
| "Explain conftest.py scoping" | "Conftest creates a hierarchy. Root conftest fixtures are available everywhere. Subdirectory conftest fixtures are scoped to that directory. pytest searches from the test file upward." |
| "When would you use session vs function scope?" | "Session for expensive one-time resources (DB connections). Function for anything tests might mutate (order objects). The tradeoff is speed vs safety." |
| "How do you test error handling?" | "I use `pytest.raises` as a context manager, then assert on the exception's attributes (field name, error code) — not just the message string." |
| "How do you handle test data?" | "Factory fixtures with sensible defaults. Call `make_order(symbol='TSLA')` to override only what differs. This scales better than one fixture per scenario." |
| "How do you keep CI fast?" | "Marks (`smoke`, `slow`). CI runs smoke first (fast gate), then full suite. Coverage gate at 80% catches untested code. Parallel execution with xdist." |
| "Walk me through your CI pipeline" | "Every PR: lint, typecheck, tests with 80% coverage gate, HTML report uploaded as artifact. Matrix tested on Python 3.11 and 3.12." |

---

*This document is part of the SET Preparation Roadmap — Phase 1, Project 1.*
