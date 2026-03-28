"""Integration tests: submit orders to a live HTTP server.

Uses a module-scoped fixture to start/stop the server.
"""

import json
import urllib.request

import pytest

from src.models.order import Order, Side, OrderType
from tests.integration.conftest import OrderSubmissionHandler


@pytest.mark.integration
class TestOrderSubmission:
    """Test order submission against a live in-process HTTP server."""

    def _submit_order(self, host: str, port: int, order: Order) -> dict:
        """Helper: POST an order to the test server."""
        payload = json.dumps({
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "order_type": order.order_type.value,
        }).encode()

        req = urllib.request.Request(
            f"http://{host}:{port}/orders",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def test_submit_buy_order(self, http_server: tuple, sample_buy_order: Order) -> None:
        host, port = http_server
        result = self._submit_order(host, port, sample_buy_order)
        assert result["status"] == "accepted"
        assert result["order_id"] == sample_buy_order.order_id

    def test_submit_sell_order(self, http_server: tuple, sample_sell_order: Order) -> None:
        host, port = http_server
        result = self._submit_order(host, port, sample_sell_order)
        assert result["status"] == "accepted"

    def test_submit_market_order(self, http_server: tuple, sample_market_order: Order) -> None:
        host, port = http_server
        result = self._submit_order(host, port, sample_market_order)
        assert result["status"] == "accepted"

    def test_server_receives_all_orders(self, http_server: tuple, make_order) -> None:
        """After submitting 3 orders above + 2 more, verify server received them."""
        host, port = http_server
        initial_count = len(OrderSubmissionHandler.received_orders)

        for sym in ["NVDA", "META"]:
            order = make_order(symbol=sym)
            self._submit_order(host, port, order)

        assert len(OrderSubmissionHandler.received_orders) == initial_count + 2

    def test_invalid_json_returns_400(self, http_server: tuple) -> None:
        """Submit invalid JSON — server should return 400."""
        host, port = http_server
        req = urllib.request.Request(
            f"http://{host}:{port}/orders",
            data=b"not json at all",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            assert False, "Expected HTTP 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
