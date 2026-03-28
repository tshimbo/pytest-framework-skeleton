"""Integration-level conftest.py — fixtures for integration tests.

These fixtures spin up heavier resources (servers, connections)
and are scoped at the module level for efficiency.
"""

import http.server
import threading
import json
from typing import Generator

import pytest


class OrderSubmissionHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP handler that accepts order submissions via POST."""

    # Class-level storage for received orders
    received_orders: list[dict] = []

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            order_data = json.loads(body)
            OrderSubmissionHandler.received_orders.append(order_data)
            response = {"status": "accepted", "order_id": order_data.get("order_id", "unknown")}
            self.send_response(200)
        except json.JSONDecodeError:
            response = {"status": "error", "message": "Invalid JSON"}
            self.send_response(400)

        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args) -> None:  # type: ignore[override]
        """Suppress server logs during tests."""
        pass


@pytest.fixture(scope="module")
def http_server() -> Generator[tuple[str, int], None, None]:
    """Spin up an in-process HTTP server for integration testing.

    Yields the (host, port) tuple. Tears down cleanly after the module.
    """
    OrderSubmissionHandler.received_orders = []
    server = http.server.HTTPServer(("localhost", 0), OrderSubmissionHandler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"\n[FIXTURE] HTTP server started on localhost:{port}")
    yield ("localhost", port)

    server.shutdown()
    print(f"\n[FIXTURE] HTTP server stopped")
