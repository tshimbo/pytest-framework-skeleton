"""Integration tests: submit orders to a live HTTP server.

WHAT IS AN INTEGRATION TEST?
    Unit tests: call ONE function, mock everything else.
    Integration tests: connect REAL components and test them together.

    Here we test:
        [Python test] ──HTTP POST──> [Real HTTP server] ──parses JSON──> [stores order]

    This is a miniature version of what Project 5 will do:
        [Test initiator] ──FIX msg──> [FIX acceptor] ──processes──> [sends ExecutionReport]

KEY CONCEPTS:
    1. Module-scoped HTTP server fixture (from integration conftest.py)
    2. urllib.request for making HTTP calls (stdlib, no external dependencies)
    3. Negative testing (sending bad JSON, expecting HTTP 400)
    4. State verification (checking what the server received)
    5. Helper methods (_submit_order) — not test methods, just utilities

WHY NOT USE requests LIBRARY?
    We use urllib.request (stdlib) to keep dependencies minimal.
    In later projects we'll use `requests` and `httpx`, but for Project 1
    we demonstrate that stdlib is sufficient.
"""

import json              # For serialising Order data to JSON
import urllib.request    # Python's built-in HTTP client (no pip install needed)

import pytest

from src.models.order import Order
# Direct import of the handler class to inspect its received_orders list.
# In a real system, you'd query an API instead of peeking at server internals.
from tests.integration.conftest import OrderSubmissionHandler


@pytest.mark.integration
class TestOrderSubmission:
    """Test order submission against a live in-process HTTP server.

    @pytest.mark.integration marks the ENTIRE class.
    All methods inside inherit the mark, so:
        make integration   → runs all 5 tests in this class
        pytest -m "not integration"  → skips all 5

    WHY USE A CLASS?
        1. Groups related tests logically
        2. Allows shared helper methods (_submit_order)
        3. Makes test output organised:
             TestOrderSubmission::test_submit_buy_order PASSED
             TestOrderSubmission::test_submit_sell_order PASSED
    """

    def _submit_order(self, host: str, port: int, order: Order) -> dict:
        """Helper: POST an order to the test server.

        WHY IS THIS A HELPER (not a test)?
            Method name starts with _ (underscore), not test_.
            pytest will NOT discover it as a test.
            It's just a utility function that multiple tests call.

        WHAT IT DOES:
            1. Serialise the Order to a JSON dict
            2. Build an HTTP POST request
            3. Send it to the server
            4. Parse and return the JSON response

        NOTE ON .value:
            order.side is Side.BUY (an Enum object).
            order.side.value is "BUY" (a plain string).
            JSON can't serialise Enum objects, so we extract .value.
        """
        # Convert Order object to a JSON-serialisable dict
        payload = json.dumps({
            "order_id": order.order_id,          # UUID string
            "symbol": order.symbol,               # e.g., "AAPL"
            "side": order.side.value,             # .value extracts "BUY" from Side.BUY
            "quantity": order.quantity,            # int
            "price": order.price,                 # float or None
            "order_type": order.order_type.value,  # .value extracts "LIMIT" from OrderType.LIMIT
        }).encode()  # .encode() converts str → bytes (HTTP needs bytes)

        # Build the HTTP request
        req = urllib.request.Request(
            f"http://{host}:{port}/orders",       # URL
            data=payload,                          # POST body
            headers={"Content-Type": "application/json"},  # Tell server it's JSON
            method="POST",                         # HTTP method
        )

        # Send the request and parse the response
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())  # bytes → str → dict

    def test_submit_buy_order(self, http_server: tuple, sample_buy_order: Order) -> None:
        """Submit a BUY order and verify the server accepted it.

        FIXTURE COMPOSITION:
            This test uses TWO fixtures from DIFFERENT conftest files:
              - http_server      ← from tests/integration/conftest.py (module-scoped)
              - sample_buy_order ← from tests/conftest.py (function-scoped, root)

            pytest resolves both automatically. The server is already running
            (started when the first test in this module needed it).
        """
        host, port = http_server  # Unpack the (host, port) tuple
        result = self._submit_order(host, port, sample_buy_order)
        assert result["status"] == "accepted"
        assert result["order_id"] == sample_buy_order.order_id  # Server echoed our ID

    def test_submit_sell_order(self, http_server: tuple, sample_sell_order: Order) -> None:
        """Submit a SELL order — verify acceptance."""
        host, port = http_server
        result = self._submit_order(host, port, sample_sell_order)
        assert result["status"] == "accepted"

    def test_submit_market_order(self, http_server: tuple, sample_market_order: Order) -> None:
        """Submit a MARKET order (no price) — verify acceptance."""
        host, port = http_server
        result = self._submit_order(host, port, sample_market_order)
        assert result["status"] == "accepted"

    def test_server_receives_all_orders(self, http_server: tuple, make_order) -> None:
        """After previous tests + 2 more, verify server received them all.

        HOW THIS WORKS:
            1. The tests above already submitted 3 orders (buy, sell, market)
               Those are stored in OrderSubmissionHandler.received_orders (class-level list)
            2. We record the current count (initial_count)
            3. We submit 2 more orders (NVDA, META)
            4. We verify the count increased by exactly 2

        WHY initial_count INSTEAD OF ASSERTING == 5?
            Because test execution order could vary (especially with xdist parallel).
            By measuring the delta, we're robust to ordering changes.
        """
        host, port = http_server
        initial_count = len(OrderSubmissionHandler.received_orders)

        for sym in ["NVDA", "META"]:
            order = make_order(symbol=sym)  # Using the factory fixture
            self._submit_order(host, port, order)

        assert len(OrderSubmissionHandler.received_orders) == initial_count + 2

    def test_invalid_json_returns_400(self, http_server: tuple) -> None:
        """Submit invalid JSON — server should return HTTP 400 Bad Request.

        NEGATIVE TESTING:
            Good tests don't just verify the "happy path" (valid input).
            They also verify that the system handles BAD input correctly.

            Here we send garbage bytes ("not json at all") and assert:
            1. The server responds with HTTP 400 (not 500 server error)
            2. The server doesn't crash (it keeps running for other tests)

        HOW urllib.error.HTTPError WORKS:
            When a server returns 4xx or 5xx, urllib.request.urlopen() raises
            urllib.error.HTTPError. We catch it and check the status code.

            The try/except pattern here is:
                try:
                    urlopen(req)           # This SHOULD raise
                    assert False, "..."    # If it doesn't, FAIL the test
                except HTTPError as e:
                    assert e.code == 400   # Verify the right error code
        """
        host, port = http_server
        req = urllib.request.Request(
            f"http://{host}:{port}/orders",
            data=b"not json at all",  # ← Deliberately invalid JSON
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            assert False, "Expected HTTP 400"  # If we get here, the test fails
        except urllib.error.HTTPError as e:
            assert e.code == 400  # PASS Server correctly rejected bad input
