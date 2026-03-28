"""Root conftest.py — shared fixtures available to ALL tests.

Fixture scoping:
  - session: created once per test session (e.g., DB connection stub)
  - module:  created once per test module
  - function: created fresh for every test (default)
"""

import json
import time
from datetime import datetime
from typing import Generator

import pytest

from src.models.order import Order, OrderType, OrderStatus, Side


# ---------------------------------------------------------------------------
# Session-scoped fixtures (initialised ONCE for the entire test run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_connection() -> Generator[dict, None, None]:
    """Simulate a session-scoped database connection.

    In a real system this would be a connection pool.
    Here we prove it only initialises once by recording timestamps.
    """
    conn = {
        "host": "localhost",
        "port": 5432,
        "db": "test_trading",
        "connected_at": datetime.utcnow().isoformat(),
        "query_count": 0,
    }
    print(f"\n[FIXTURE] DB connection opened at {conn['connected_at']}")
    yield conn
    print(f"\n[FIXTURE] DB connection closed. Queries executed: {conn['query_count']}")


@pytest.fixture(scope="session")
def test_session_id() -> str:
    """Generate a unique session ID for this test run."""
    return f"test-session-{int(time.time())}"


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def order_book() -> dict:
    """A shared in-memory order book for a test module.

    Returns a dict mapping order_id → Order.
    """
    return {}


# ---------------------------------------------------------------------------
# Function-scoped fixtures (fresh for every test)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_buy_order() -> Order:
    """A valid BUY LIMIT order for AAPL."""
    return Order(
        symbol="AAPL",
        side=Side.BUY,
        quantity=100,
        price=150.50,
        order_type=OrderType.LIMIT,
    )


@pytest.fixture
def sample_sell_order() -> Order:
    """A valid SELL LIMIT order for AAPL."""
    return Order(
        symbol="AAPL",
        side=Side.SELL,
        quantity=50,
        price=155.00,
        order_type=OrderType.LIMIT,
    )


@pytest.fixture
def sample_market_order() -> Order:
    """A valid MARKET BUY order for GOOGL."""
    return Order(
        symbol="GOOGL",
        side=Side.BUY,
        quantity=200,
        order_type=OrderType.MARKET,
    )


@pytest.fixture
def make_order():
    """Factory fixture — call it with overrides to create custom orders.

    Usage:
        order = make_order(symbol="TSLA", quantity=500)
    """
    def _make_order(**kwargs) -> Order:
        defaults = {
            "symbol": "AAPL",
            "side": Side.BUY,
            "quantity": 100,
            "price": 150.00,
            "order_type": OrderType.LIMIT,
        }
        defaults.update(kwargs)
        return Order(**defaults)
    return _make_order


# ---------------------------------------------------------------------------
# pytest hooks — live test logging
# ---------------------------------------------------------------------------

def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Custom hook: log PASSED/FAILED with timestamps to stdout."""
    if report.when == "call":
        timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        outcome = report.outcome.upper()
        duration = f"{report.duration:.3f}s"
        print(f"  [{timestamp}] {outcome} {report.nodeid} ({duration})")


def pytest_configure(config: pytest.Config) -> None:
    """Add metadata to the HTML report."""
    if hasattr(config, "_metadata"):
        config._metadata["Project"] = "pytest-framework-skeleton"
        config._metadata["Framework Version"] = "0.1.0"
