"""Deterministic unit tests for the order-status API.
Run with:  pytest -q
"""

from datetime import date

from fastapi.testclient import TestClient

from main import app, get_orders, OrderStatus

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_orders_returns_all():
    r = client.get("/orders")
    assert r.status_code == 200
    assert len(r.json()) == 4


def test_healthy_order_not_delayed():
    r = client.get("/orders/ORD-1001")
    assert r.status_code == 200
    body = r.json()
    assert body["is_delayed"] is False
    assert body["payment_status"] == "Paid"


def test_delayed_order_is_flagged():
    """Past ship date + still Processing -> delayed -> agent should escalate."""
    r = client.get("/orders/ORD-1002")
    assert r.status_code == 200
    body = r.json()
    assert body["order_status"] == "Processing"
    assert body["is_delayed"] is True


def test_delivered_past_date_not_delayed():
    """Past ship date but already delivered -> NOT delayed (no escalation)."""
    r = client.get("/orders/ORD-1003")
    assert r.status_code == 200
    assert r.json()["is_delayed"] is False


def test_unknown_order_returns_404():
    r = client.get("/orders/ORD-9999")
    assert r.status_code == 404


def test_order_number_is_normalized():
    """Bare digits and lowercase should resolve to the same order."""
    assert client.get("/orders/1002").status_code == 200
    assert client.get("/orders/ord-1002").status_code == 200


def test_delay_rule_directly():
    """Sanity-check the rule against today's computed data."""
    orders = get_orders(date.today())
    assert orders["ORD-1002"].is_delayed is True
    assert orders["ORD-1001"].is_delayed is False
    assert orders["ORD-1002"].order_status == OrderStatus.processing
