# Playto Founding Engineer Challenge - Payout Engine

Minimal payout engine implementation focused on money integrity, concurrency safety, idempotency, and async processing.

## Stack

- Backend: Django + DRF
- Database: PostgreSQL
- Background jobs: Celery + Redis
- Frontend: React + Tailwind (minimal dashboard)

## Implemented Scope

- Merchant ledger with paise integers (`BigIntegerField`)
- Derived balance at query time (no stored balance field)
- `POST /api/v1/payouts` with `Idempotency-Key`
- Idempotency keys scoped by merchant with 24-hour expiry
- Background payout processor with 70/20/10 outcomes
- Retry for stuck processing payouts with exponential backoff, max 3 attempts
- State machine enforcement (`pending -> processing -> completed|failed`)
- Atomic refund on failure
- React dashboard showing available/held balance, payout history, and ledger entries
- Tests for idempotency and concurrent overdraw prevention

## Repository Layout

- backend/ - Django app
- frontend/ - React + Tailwind app
- EXPLAINER.md - architecture and correctness explanation

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

## Quick Dependency Start (Docker)

From project root:

```bash
docker run --name demo-postgres -e POSTGRES_DB=payout -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16
docker run --name demo-redis -p 6379:6379 -d redis:7
```

If already created:

```bash
docker start demo-postgres
docker start demo-redis
```

## Backend Setup

From `backend`:

### cmd

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

set POSTGRES_DB=payout
set POSTGRES_USER=postgres
set POSTGRES_PASSWORD=postgres
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set REDIS_URL=redis://localhost:6379/0
set DJANGO_SETTINGS_MODULE=payout_engine.settings
set DEBUG=1
set ALLOWED_HOSTS=localhost,127.0.0.1
set CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

python manage.py migrate
python manage.py seed_demo_data
```

### PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:POSTGRES_DB="payout"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:REDIS_URL="redis://localhost:6379/0"
$env:DJANGO_SETTINGS_MODULE="payout_engine.settings"
$env:DEBUG="1"
$env:ALLOWED_HOSTS="localhost,127.0.0.1"
$env:CORS_ALLOWED_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"

python manage.py migrate
python manage.py seed_demo_data
```

## Run Backend (3 terminals)

Terminal 1:

```bash
python manage.py runserver
```

Terminal 2:

```bash
celery -A payout_engine worker -l info
```

Terminal 3:

```bash
celery -A payout_engine beat -l info
```

Note for Windows: worker pool is forced to `solo` in settings to avoid `billiard` spawn errors.

## Frontend Setup (React + Tailwind)

From `frontend`:

```bash
npm install
npm run dev
```

Open:
- Frontend: `http://127.0.0.1:5173`
- Backend demo page (optional): `http://127.0.0.1:8000/`

For a separately hosted frontend build, set:

```bash
VITE_API_URL=https://your-backend.example.com/api/v1
```

## API Contract

### Balance

- `GET /api/v1/balance`
- Header: `X-Merchant-Id`

Response:

```json
{
  "available_balance_paise": 260000,
  "held_balance_paise": 5000,
  "as_of": "2026-04-26T19:00:00Z"
}
```

### Create Payout

- `POST /api/v1/payouts`
- Headers: `X-Merchant-Id`, `Idempotency-Key`
- Body:

```json
{
  "amount_paise": 5000,
  "bank_account_id": "bank_demo_001"
}
```

### List Payouts

- `GET /api/v1/payouts`
- Header: `X-Merchant-Id`

### Ledger Feed

- `GET /api/v1/ledger?limit=10`
- Header: `X-Merchant-Id`

## Seed Data

Seed command creates 3 merchants and credit history:

```bash
python manage.py seed_demo_data
```

## Tests

Run:

```bash
python manage.py test core.tests
```

Included tests:
- concurrent overdraw prevention (two simultaneous payouts, one rejected)
- idempotency replay (same key returns same payout)
- idempotency key expiry after 24 hours

## Demo Flow

1. Open React dashboard.
2. Use merchant id `1`.
3. Create payout with amount and idempotency key.
4. Re-submit with same key to show replay.
5. Observe status transitions via auto-refresh.
6. On failure, verify refund behavior via ledger and balance.

## Submission Checklist

Before submitting, verify all boxes:

- Code pushed to GitHub with clean commit history
- Backend deployed (public URL)
- Frontend deployed (public URL)
- Database migrated on deployed environment
- Seed command executed on deployed environment
- Same idempotency key replay verified in deployed app
- At least one failure-refund cycle observed and documented
- Tests executed successfully (`python manage.py test core.tests`)
- EXPLAINER.md included in repository root

## Deployment Details (fill before submit)

- Frontend URL: TODO
- Backend URL: TODO
- API base: TODO
- Demo merchant IDs: 1, 2, 3
- Suggested idempotency keys for demo:
  - demo-key-101
  - demo-key-102
  - demo-key-103

## 2-Minute Demo Script

1. Open frontend and select merchant `1`.
2. Create payout with INR amount and key `demo-key-101`.
3. Repeat same request with same key to show idempotency replay.
4. Create two more payouts with new keys to show async transitions.
5. Point to ledger row when a payout fails and refund credit appears.
6. Explain available vs held balance changes.

## Troubleshooting

1. `module payout_engine was not found`
- Run commands from `backend` folder.

2. `connection refused localhost:5432`
- PostgreSQL is not running.

3. `relation core_merchant does not exist`
- Run migrations.

4. Celery WinError 5/6 on Windows
- Use configured solo pool (already set in settings).

5. `$env:` syntax error
- You are in cmd. Use `set KEY=value` in cmd, `$env:KEY="value"` in PowerShell.
