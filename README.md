# Order Status API

A small mock service (Python + FastAPI) that returns order details for a
**Microsoft Copilot Studio** conversational agent. All data is simulated and
held in memory — no database required.

## Endpoints

| Method | Path | Description |
| ------ | ------------------------ | ------------------------------------------ |
| GET | `/health` (and `/`) | Health check / warm-up ping |
| GET | `/orders` | List all seeded orders |
| GET | `/orders/{order_number}` | Single order, or `404` if it doesn't exist |

Interactive docs are auto-generated at **`/docs`** (Swagger UI).

### Example response (`GET /orders/ORD-1002`)

```json
{
  "order_number": "ORD-1002",
  "order_status": "Processing",
  "order_date": "2026-06-08",
  "total_value": 1299.0,
  "currency": "PLN",
  "payment_status": "Paid",
  "estimated_shipping_date": "2026-06-17",
  "is_delayed": true
}
```

## The `is_delayed` flag

This is the field that drives escalation. It is computed **on the server** so
the rule lives in one place, is unit-tested, and the agent does no date math:

```
is_delayed = (estimated_shipping_date < today)
             AND (status is not Shipped / In Transit / Delivered / Cancelled)
```

So only an order that is still **Processing** past its shipping date is flagged.
A delivered order with a past date is *not* delayed.

## Seeded orders

| Order | Status | Payment | Ship date | Delayed? |
| -------- | ----------- | ------- | --------------- | ----------------------- |
| ORD-1001 | In Transit | Paid | today + 2 | No (happy path) |
| ORD-1002 | Processing | Paid | today − 5 | **Yes** (escalation) |
| ORD-1003 | Delivered | Paid | today − 7 | No (delivered edge case)|
| ORD-1004 | Processing | Pending | today + 5 | No (payment pending) |

Dates are relative to *today*, so the demo is always valid whenever it runs.
Lookups are forgiving: `1002`, `ord-1002` and `ORD-1002` all resolve.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# open http://127.0.0.1:8000/docs
```

## Run the tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Deploy

Requires **Python 3.11+**. Start command (all platforms):

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Render (free)
1. Push this folder to a GitHub repo.
2. Render → **New → Web Service** → connect the repo.
3. Build command: `pip install -r requirements.txt`
   Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Deploy. You get an `https://<name>.onrender.com` URL.

> ⚠️ Free Render services **sleep** after inactivity → first request can take
> ~50 s (cold start). Hit `/health` ~1 min before any live demo to warm it up.

### Railway
1. Push to GitHub → Railway → **New Project → Deploy from GitHub**.
2. Railway autodetects the Procfile / Python. Add a public domain in
   **Settings → Networking → Generate Domain**.

## Optional: API key

Set an `API_KEY` environment variable on the host to require callers to send
`X-API-Key: <value>`. Leave it unset for an open demo.
