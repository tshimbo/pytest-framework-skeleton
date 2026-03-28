"""Root conftest.py — shared fixtures available to ALL tests.

WHAT IS conftest.py?
    conftest.py is a MAGIC filename that pytest automatically discovers.
    Any fixture defined here is automatically available to every test in
    this directory AND all subdirectories. You never need to import it.

    Think of it like a "shared toolbox" that every test can reach into.

CONFTEST HIERARCHY (how fixtures cascade):
    tests/conftest.py              ← THIS FILE. Available to ALL tests.
    tests/unit/conftest.py         ← Available to tests/unit/** ONLY.
    tests/integration/conftest.py  ← Available to tests/integration/** ONLY.

    If a unit test asks for a fixture, pytest searches:
      1. The test file itself
      2. tests/unit/conftest.py    (closest conftest)
      3. tests/conftest.py         (this file — parent conftest)
    The FIRST match wins. This lets sub-level conftest.py files override root ones.

FIXTURE SCOPES (how long a fixture lives):
    scope="session"   → Created ONCE for the entire test run. Destroyed at the very end.
                        Use for: expensive resources (DB connections, Docker containers).
    scope="module"    → Created once per test MODULE (file). Destroyed after the last test in that file.
                        Use for: medium-cost resources (HTTP servers, file handles).
    scope="class"     → Created once per test CLASS. Destroyed after the last method in that class.
    scope="function"  → Created fresh for EVERY test function (DEFAULT).
                        Use for: anything that tests might mutate (order objects, counters).

    WHY SCOPES MATTER:
        Broader scopes (session, module) = faster tests (less setup/teardown)
        Narrower scopes (function) = safer tests (no shared mutable state)
        The art is picking the right scope for each fixture.

WHAT IS yield IN A FIXTURE?
    A fixture with `yield` is a "setup/teardown" fixture:
        1. Code BEFORE yield runs during SETUP
        2. The yielded value is passed to the test
        3. Code AFTER yield runs during TEARDOWN (even if the test fails!)

    Example:
        @pytest.fixture
        def db():
            conn = connect()    # SETUP: open connection
            yield conn           # TEST RUNS HERE with conn
            conn.close()         # TEARDOWN: always close, even on failure

HOW THIS MAPS TO CITADEL SECURITIES:
    An SET at Citadel would write conftest fixtures for:
    - FIX session connections (session-scoped)
    - Mock exchange servers (module-scoped)
    - Order objects for each test (function-scoped)
    Interviewers often ask: "What scope would you use for X and why?"
"""

# ─── IMPORTS ────────────────────────────────────────────────────────────────
import json
import time
from datetime import datetime
from typing import Generator

import pytest  # The testing framework. Provides @pytest.fixture, marks, hooks, etc.

# Import our own source code so fixtures can create Order objects.
from src.models.order import Order, OrderType, OrderStatus, Side


# ═══════════════════════════════════════════════════════════════════════
# SESSION-SCOPED FIXTURES
# Created ONCE for the entire test run. Shared across ALL test files.
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def db_connection() -> Generator[dict, None, None]:
    """Simulate a session-scoped database connection.

    HOW THIS WORKS:
        1. SETUP: Creates a dict simulating a DB connection.
        2. YIELD: Gives that dict to any test that requests `db_connection`.
        3. TEARDOWN: Prints how many queries ran (after ALL tests finish).

    WHY session SCOPE?
        Opening a real DB connection is expensive (network round-trip, auth, etc.).
        We want to do it ONCE and reuse it for every test. Session scope ensures
        this fixture is created when the first test needs it and destroyed only
        after the last test in the entire session finishes.

    HOW TO VERIFY IT'S ONLY CREATED ONCE:
        Run: pytest -v -s    (the -s flag shows print output)
        You'll see "DB connection opened" printed exactly ONCE, no matter
        how many tests use this fixture.

    GENERATOR TYPE HINT:
        Generator[YieldType, SendType, ReturnType]
        Generator[dict, None, None] means:
            - yields a dict
            - doesn't accept sent values (None)
            - doesn't return a value (None)
    """
    # --- SETUP PHASE ---
    conn = {
        "host": "localhost",
        "port": 5432,
        "db": "test_trading",
        "connected_at": datetime.utcnow().isoformat(),
        "query_count": 0,  # Tests can increment this to simulate queries
    }
    print(f"\n[FIXTURE] DB connection opened at {conn['connected_at']}")

    yield conn  # <-- Test runs here, with access to `conn`

    # --- TEARDOWN PHASE --- (runs even if tests fail!)
    print(f"\n[FIXTURE] DB connection closed. Queries executed: {conn['query_count']}")


@pytest.fixture(scope="session")
def test_session_id() -> str:
    """Generate a unique session ID for this test run.

    This is useful for:
        - Tagging log lines so you can trace which test run produced them
        - Prefixing temporary resources (e.g., test_session_12345_orders table)
        - Correlating CI artifacts with specific runs

    Uses int(time.time()) which gives seconds since epoch (e.g., 1711584000).
    Simple but unique enough for testing purposes.
    """
    return f"test-session-{int(time.time())}"


# ═══════════════════════════════════════════════════════════════════════
# MODULE-SCOPED FIXTURES
# Created once per test MODULE (file). Shared across tests in that file.
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def order_book() -> dict:
    """A shared in-memory order book for a test module.

    Returns a dict mapping order_id → Order.
    Module-scoped so all tests in one file share the same book.

    WARNING: Because this is shared, if one test adds an order,
    the next test in the same file will see it. This is intentional
    for testing stateful workflows, but can cause surprises.
    In Project 6, we'll build a real OrderBook class here.
    """
    return {}


# ═══════════════════════════════════════════════════════════════════════
# FUNCTION-SCOPED FIXTURES (DEFAULT SCOPE)
# Created fresh for EVERY test that requests them.
# This is the safest scope — no shared mutable state between tests.
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_buy_order() -> Order:
    """A valid BUY LIMIT order for AAPL.

    HOW FIXTURES WORK:
        A test simply names this fixture in its parameter list:

            def test_something(self, sample_buy_order):
                assert sample_buy_order.side == Side.BUY

        pytest sees the parameter name "sample_buy_order", looks it up in
        the fixture registry, calls this function, and passes the result
        to the test. No import needed. This is called DEPENDENCY INJECTION.

    WHY function SCOPE (default)?
        Because tests might mutate the order (change status, fill quantity).
        Each test needs its OWN fresh copy so changes don't leak between tests.
    """
    return Order(
        symbol="AAPL",
        side=Side.BUY,
        quantity=100,
        price=150.50,
        order_type=OrderType.LIMIT,
    )


@pytest.fixture
def sample_sell_order() -> Order:
    """A valid SELL LIMIT order for AAPL.

    Having both buy and sell fixtures lets us test both sides of a trade
    without constructing orders inline in every test.
    """
    return Order(
        symbol="AAPL",
        side=Side.SELL,
        quantity=50,
        price=155.00,
        order_type=OrderType.LIMIT,
    )


@pytest.fixture
def sample_market_order() -> Order:
    """A valid MARKET BUY order for GOOGL.

    Note: price is NOT set (defaults to None).
    MARKET orders don't have a price — the exchange matches at the best available.
    This is important for testing the validator's price rules.
    """
    return Order(
        symbol="GOOGL",
        side=Side.BUY,
        quantity=200,
        order_type=OrderType.MARKET,
    )


@pytest.fixture
def make_order():
    """Factory fixture — call it with overrides to create custom orders.

    WHAT IS A FACTORY FIXTURE?
        Instead of returning a fixed object, this returns a FUNCTION.
        Tests call that function with keyword arguments to create
        customised orders on-the-fly:

            def test_tsla(self, make_order):
                order = make_order(symbol="TSLA", quantity=500)

    WHY USE A FACTORY?
        - sample_buy_order gives you ONE specific order. What if you need 10?
        - A factory lets you create any number of orders with any combination of fields.
        - The defaults dict provides sane defaults so you only specify what differs.

    PATTERN:
        This is the "Factory Pattern" adapted for pytest. It's extremely common
        in real test frameworks. You'll see it again in Projects 5-10.
    """
    def _make_order(**kwargs) -> Order:
        # Start with sensible defaults for every field
        defaults = {
            "symbol": "AAPL",
            "side": Side.BUY,
            "quantity": 100,
            "price": 150.00,
            "order_type": OrderType.LIMIT,
        }
        # dict.update() merges kwargs INTO defaults, overriding any matching keys.
        # So make_order(symbol="TSLA") gives you TSLA with all other fields as defaults.
        defaults.update(kwargs)
        # **defaults unpacks the dict as keyword arguments to Order()
        # This is equivalent to: Order(symbol="TSLA", side=Side.BUY, quantity=100, ...)
        return Order(**defaults)
    return _make_order


# ═══════════════════════════════════════════════════════════════════════
# PYTEST HOOKS
# Hooks are special functions that pytest calls at specific points during
# test execution. They let you customise pytest's behaviour without
# modifying pytest itself.
# ═══════════════════════════════════════════════════════════════════════

def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Custom hook: log PASSED/FAILED with timestamps to stdout.

    WHAT IS THIS HOOK?
        pytest calls this function after EACH test phase (setup, call, teardown).
        We only care about the "call" phase (the actual test execution).

    WHEN DOES IT FIRE?
        report.when == "setup"    → after fixture setup
        report.when == "call"     → after the test function itself  ← we want this
        report.when == "teardown" → after fixture teardown

    WHAT DOES report CONTAIN?
        report.nodeid   = "tests/unit/test_order_model.py::TestOrderCreation::test_buy"
        report.outcome  = "passed" | "failed" | "skipped"
        report.duration = 0.003 (seconds)

    WHY USE THIS?
        - See live progress during long test runs
        - Timestamps help identify slow tests
        - This is a stepping stone to Project 9's full observability stack
    """
    if report.when == "call":  # Only log the actual test, not setup/teardown
        timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        outcome = report.outcome.upper()       # "PASSED" or "FAILED"
        duration = f"{report.duration:.3f}s"    # e.g., "0.003s"
        print(f"  [{timestamp}] {outcome} {report.nodeid} ({duration})")


def pytest_configure(config: pytest.Config) -> None:
    """Add metadata to the HTML report.

    WHAT IS THIS HOOK?
        Called once at the very start of a test session, before any collection.
        We use it to inject metadata that appears in the HTML report header.

    WHAT IS config._metadata?
        pytest-metadata plugin adds a _metadata dict to config.
        Any key-value pair we add here shows up in the HTML report's
        "Environment" section. Useful for tracking:
        - Which build produced this report
        - Git commit SHA
        - Python version
        - Custom project info
    """
    if hasattr(config, "_metadata"):
        config._metadata["Project"] = "pytest-framework-skeleton"
        config._metadata["Framework Version"] = "0.1.0"
