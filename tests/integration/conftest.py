"""Integration-level conftest.py — fixtures for integration tests.

WHAT ARE INTEGRATION TESTS?
    Unit tests test ONE function in isolation (no network, no servers, no I/O).
    Integration tests test how multiple components work TOGETHER.
    Here, we test our Order model + a real HTTP server + actual network requests.

WHAT THIS FILE PROVIDES:
    A real HTTP server that runs inside the test process.
    Tests can POST orders to it and verify responses — just like
    a real OMS would submit orders to an exchange over HTTP/FIX.

WHY MODULE SCOPE?
    Starting a server is expensive (~100ms). We start it ONCE per test file
    and share it across all tests in that file. Each test gets the same server
    but tests are independent because we track state explicitly.

KEY PYTHON CONCEPTS:
    1. http.server.HTTPServer       — Python's built-in HTTP server
    2. BaseHTTPRequestHandler       — defines how to handle GET, POST, etc.
    3. threading.Thread(daemon=True) — runs server in background, dies with main thread
    4. port 0                        — OS assigns a random available port (avoids conflicts)
    5. Generator fixture with yield  — setup (start server) / teardown (stop server)
"""

import http.server  # Python's built-in HTTP server module
import threading     # For running the server in a background thread
import json          # For parsing JSON request bodies and building JSON responses
from typing import Generator

import pytest


class OrderSubmissionHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP handler that accepts order submissions via POST.

    HOW HTTP HANDLERS WORK:
        When a request arrives, Python calls the method matching the HTTP verb:
            GET  /orders  → calls do_GET()
            POST /orders  → calls do_POST()    ← we implement this one
            PUT  /orders  → calls do_PUT()

        We only implement do_POST because our test scenario is:
        "client submits an order (POST), server accepts or rejects it."

    CLASS-LEVEL STATE:
        `received_orders` is a CLASS variable (shared across all instances).
        Every time a POST arrives, we append the order data to this list.
        Tests can check this list to verify the server received the right data.

    IN A REAL SYSTEM:
        This would be a FIX acceptor (Project 5) or a REST API gateway.
        The handler would validate the order, pass it to the matching engine,
        and return an ExecutionReport.
    """

    # Class-level storage — shared across all handler instances.
    # This is how we let tests inspect what the server received.
    received_orders: list[dict] = []

    def do_POST(self) -> None:
        """Handle POST requests — accept order submissions.

        Steps:
            1. Read the request body (raw bytes)
            2. Parse it as JSON
            3. If valid: store the order, respond with 200 + order_id
            4. If invalid JSON: respond with 400 error
        """
        # ── Step 1: Read the request body ────────────────────────────
        # Content-Length header tells us how many bytes to read.
        # Without this, rfile.read() would block forever waiting for more data.
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)  # Read exactly that many bytes

        # ── Step 2: Parse JSON ───────────────────────────────────
        try:
            order_data = json.loads(body)  # bytes → dict
            OrderSubmissionHandler.received_orders.append(order_data)
            response = {
                "status": "accepted",
                "order_id": order_data.get("order_id", "unknown")
            }
            self.send_response(200)  # HTTP 200 OK
        except json.JSONDecodeError:
            # Bad JSON → 400 Bad Request
            response = {"status": "error", "message": "Invalid JSON"}
            self.send_response(400)  # HTTP 400 Bad Request

        # ── Step 3: Send response ───────────────────────────────
        self.send_header("Content-Type", "application/json")
        self.end_headers()  # Blank line separating headers from body (HTTP spec)
        self.wfile.write(json.dumps(response).encode())  # dict → JSON string → bytes

    def log_message(self, format, *args) -> None:  # type: ignore[override]
        """Suppress server logs during tests.

        By default, BaseHTTPRequestHandler prints every request to stderr:
            127.0.0.1 - - [27/Mar/2026 10:30:00] "POST /orders HTTP/1.1" 200 -
        This clutters test output, so we override log_message to do nothing.
        """
        pass  # Silence!


@pytest.fixture(scope="module")
def http_server() -> Generator[tuple[str, int], None, None]:
    """Spin up an in-process HTTP server for integration testing.

    LIFECYCLE:
        1. SETUP: Start an HTTPServer on a random port in a daemon thread
        2. YIELD: Give tests the (host, port) tuple so they can connect
        3. TEARDOWN: Shut down the server cleanly

    WHY PORT 0?
        Passing port 0 to HTTPServer tells the OS to pick any available port.
        This avoids "Address already in use" errors when running tests
        in parallel or on CI where ports might be occupied.
        After binding, we read the actual port from server.server_address[1].

    WHY daemon=True?
        A daemon thread is automatically killed when the main program exits.
        Without this, if a test crashes, the server thread would keep the
        process alive forever. With daemon=True, it dies when pytest exits.

    WHY scope="module"?
        Starting an HTTP server takes ~100ms. If we used function scope,
        we'd restart it for every single test. Module scope means we start
        it once per test file, which is much faster.
    """
    # ── SETUP PHASE ───
    # Reset the received_orders list so we start fresh for each test module
    OrderSubmissionHandler.received_orders = []

    # Create server on localhost with port 0 (OS picks a random available port)
    server = http.server.HTTPServer(("localhost", 0), OrderSubmissionHandler)
    port = server.server_address[1]  # Read the actual port the OS assigned

    # Run serve_forever() in a background thread so it doesn't block the tests
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"\n[FIXTURE] HTTP server started on localhost:{port}")
    yield ("localhost", port)  # ← Tests run here, making requests to this server

    # ── TEARDOWN PHASE ───
    server.shutdown()  # Gracefully stop the server (waits for in-flight requests)
    print(f"\n[FIXTURE] HTTP server stopped")
