"""Order Status API
A small mock service that returns order details for a Copilot Studio
conversational agent. All data is simulated and held in memory.

Key design decision: the `is_delayed` flag is computed on the server, not in
Copilot Studio. This keeps a single source of truth, makes the rule unit-testable,
and removes any date/timezone math from the Power Fx side of the agent.
"""

from datetime import date, timedelta
from enum import Enum
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Order Status API",
    description="Mock order-status service for a Copilot Studio conversational agent.",
    version="1.0.0",
)

# Permissive CORS so the API can also be exercised from a browser-based tool.
# Irrelevant for server-to-server calls from Power Platform, but harmless.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API key gate. Stays OFF unless the API_KEY env var is set.
# When set, callers must send the header  X-API-Key: <value>
API_KEY = os.getenv("API_KEY")


class OrderStatus(str, Enum):
    processing = "Processing"
    shipped = "Shipped"
    in_transit = "In Transit"
    delivered = "Delivered"
    cancelled = "Cancelled"


class PaymentStatus(str, Enum):
    paid = "Paid"
    pending = "Pending"
    failed = "Failed"


# Statuses for which a passed shipping date does NOT mean "delayed":
# the order has either already shipped or is closed.
FULFILLED_OR_CLOSED = {
    OrderStatus.shipped,
    OrderStatus.in_transit,
    OrderStatus.delivered,
    OrderStatus.cancelled,
}


class Order(BaseModel):
    order_number: str
    order_status: OrderStatus
    order_date: date
    total_value: float
    currency: str = "PLN"
    payment_status: PaymentStatus
    estimated_shipping_date: date
    is_delayed: bool = Field(
        ...,
        description=(
            "True when the estimated shipping date has passed and the order "
            "has not yet been fulfilled."
        ),
    )


# Seed data uses day offsets relative to 'today' so the demo is always correct,
# whenever it is run. Absolute dates would go stale.
ORDER_SEED = [
    {
        # Happy path: shipped and on its way, delivery still in the future.
        "order_number": "ORD-1001",
        "order_status": OrderStatus.in_transit,
        "order_date_offset": -4,
        "total_value": 249.99,
        "currency": "PLN",
        "payment_status": PaymentStatus.paid,
        "ship_date_offset": 2,
    },
    {
        # Delayed: still 'Processing' but the estimated ship date has passed.
        # This is the mandatory escalation scenario.
        "order_number": "ORD-1002",
        "order_status": OrderStatus.processing,
        "order_date_offset": -14,
        "total_value": 1299.00,
        "currency": "PLN",
        "payment_status": PaymentStatus.paid,
        "ship_date_offset": -5,
    },
    {
        # Edge case: ship date is in the past, but it was delivered -> NOT delayed.
        "order_number": "ORD-1003",
        "order_status": OrderStatus.delivered,
        "order_date_offset": -12,
        "total_value": 89.50,
        "currency": "PLN",
        "payment_status": PaymentStatus.paid,
        "ship_date_offset": -7,
    },
    {
        # Payment-pending order, ship date in the future -> not delayed,
        # but the agent has something extra to explain.
        "order_number": "ORD-1004",
        "order_status": OrderStatus.processing,
        "order_date_offset": -1,
        "total_value": 459.00,
        "currency": "PLN",
        "payment_status": PaymentStatus.pending,
        "ship_date_offset": 5,
    },
]


def _build_order(seed: dict, today: date) -> Order:
    ship_date = today + timedelta(days=seed["ship_date_offset"])
    order_status = seed["order_status"]
    is_delayed = ship_date < today and order_status not in FULFILLED_OR_CLOSED
    return Order(
        order_number=seed["order_number"],
        order_status=order_status,
        order_date=today + timedelta(days=seed["order_date_offset"]),
        total_value=seed["total_value"],
        currency=seed["currency"],
        payment_status=seed["payment_status"],
        estimated_shipping_date=ship_date,
        is_delayed=is_delayed,
    )


def get_orders(today: date) -> dict[str, Order]:
    return {seed["order_number"]: _build_order(seed, today) for seed in ORDER_SEED}


def _normalize(order_number: str) -> str:
    """Make lookups forgiving: '1002', 'ord-1002' and 'ORD-1002' all resolve."""
    cleaned = order_number.strip().upper()
    if cleaned.isdigit():
        cleaned = f"ORD-{cleaned}"
    return cleaned


def _check_key(x_api_key: str | None) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.get("/")
@app.get("/health")
def health():
    """Health check. Also handy to 'warm up' a sleeping free-tier host before a demo."""
    return {"status": "ok", "service": "order-status-api"}


@app.get("/orders", response_model=list[Order])
def list_orders(x_api_key: str | None = Header(default=None)):
    """List every seeded order. Useful for testing and during the demo."""
    _check_key(x_api_key)
    return list(get_orders(date.today()).values())


@app.get("/orders/{order_number}", response_model=Order)
def get_order(order_number: str, x_api_key: str | None = Header(default=None)):
    """Return a single order by its number, or 404 if it does not exist."""
    _check_key(x_api_key)
    orders = get_orders(date.today())
    key = _normalize(order_number)
    if key not in orders:
        raise HTTPException(
            status_code=404, detail=f"Order '{order_number}' was not found."
        )
    return orders[key]
