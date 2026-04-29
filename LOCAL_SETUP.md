# Local Development Setup (Windows)

Quick start for local development and testing.

## Prerequisites

- Docker Desktop (includes Docker Compose) - [Download](https://www.docker.com/products/docker-desktop)
- Python 3.11+ - [Download](https://www.python.org/downloads/)
- Node.js 18+ - [Download](https://nodejs.org/)
- Git - [Download](https://git-scm.com/)

## Step 1: Start Database and Cache

From project root:

```powershell
docker-compose up -d
```

Verify services running:

```powershell
docker-compose ps
```

Should show postgres and redis both "Up".

## Step 2: Backend Setup

```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set environment variables
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

# Run migrations
python manage.py migrate

# Seed demo data
python manage.py seed_demo_data

# Run tests (important!)
python manage.py test core.tests
```

Expected test output:

```
Ran 3 tests in X.XXXs

OK
```

## Step 3: Run Backend (3 Terminals)

### Terminal A: Django Development Server

```powershell
cd backend
.\venv\Scripts\Activate.ps1

$env:DJANGO_SETTINGS_MODULE="payout_engine.settings"
$env:POSTGRES_DB="payout"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:REDIS_URL="redis://localhost:6379/0"
$env:DEBUG="1"
$env:ALLOWED_HOSTS="localhost,127.0.0.1"
$env:CORS_ALLOWED_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"

python manage.py runserver
```

Should see:

```
Starting development server at http://127.0.0.1:8000/
```

### Terminal B: Celery Worker

```powershell
cd backend
.\venv\Scripts\Activate.ps1

$env:DJANGO_SETTINGS_MODULE="payout_engine.settings"
$env:POSTGRES_DB="payout"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:REDIS_URL="redis://localhost:6379/0"
$env:DEBUG="1"

celery -A payout_engine worker -l info
```

Should see:

```
connected to redis://localhost:6379/0
Ready to accept tasks
```

### Terminal C: Celery Beat (Task Scheduler)

```powershell
cd backend
.\venv\Scripts\Activate.ps1

$env:DJANGO_SETTINGS_MODULE="payout_engine.settings"
$env:POSTGRES_DB="payout"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:REDIS_URL="redis://localhost:6379/0"
$env:DEBUG="1"

celery -A payout_engine beat -l info
```

Should see periodic task schedule.

## Step 4: Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Optional for a separately hosted frontend build:

```powershell
$env:VITE_API_URL="http://127.0.0.1:8000/api/v1"
npm run dev
```

Should show:

```
  VITE v5.x.x
  ➜  Local:   http://127.0.0.1:5173/
```

## Step 5: Test Manually

1. Open browser: **http://127.0.0.1:5173**

2. Merchant ID selector shows "1" (Alpha Agency with 2000 INR available)

3. Create payout:
   - Amount: 600.00 INR
   - Account: bank_demo_001
   - Key: test-key-001
   - Click Submit

4. Verify response shows payout created with status "pending"

5. **Repeat with same key** → Should return same payout (HTTP 200, not 201)

6. Watch payout status cycle:
   - pending → processing (5s)
   - processing → completed (or failed)

7. On failure, check ledger shows refund credit

## Testing Concurrency & Idempotency

```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE="payout_engine.settings"
# [Set other env vars as above]

python manage.py test core.tests.PayoutEngineTests.test_concurrent_overdraw_allows_only_one_payout -v 2
python manage.py test core.tests.PayoutEngineTests.test_idempotency_same_key_returns_same_payout -v 2
```

## Cleanup

Stop all services:

```powershell
# Kill Django (Ctrl+C in terminal)
# Kill Celery Worker (Ctrl+C in terminal)
# Kill Celery Beat (Ctrl+C in terminal)
# Stop Docker services:
docker-compose down
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'django'"
- Ensure venv is activated: `.\venv\Scripts\Activate.ps1`
- Reinstall requirements: `pip install -r requirements.txt`

### "psycopg2: could not translate host name "localhost" to address"
- PostgreSQL not running: `docker-compose ps`
- Start Docker: `docker-compose up -d`

### "Connection refused: ('127.0.0.1', 6379)"
- Redis not running: Check `docker-compose ps`
- Restart: `docker-compose restart redis`

### Celery: "billiard.exceptions.SoftTimeLimitExceeded"
- Windows issue with multiprocessing
- Already fixed in settings.py (solo pool forced)

### Tests fail with "UNIQUE constraint failed"
- Database state corrupted, reset:
  ```
  python manage.py flush --noinput
  python manage.py seed_demo_data
  ```

## Demo Flow (for Playto evaluators)

1. Open dashboard at http://127.0.0.1:5173
2. Merchant 1 has 2000 INR available
3. Create payout: 600 INR
4. Re-submit same request with same idempotency key → returns same payout
5. Create two more payouts to see processing
6. Observe status transitions every 3-5 seconds
7. When failure occurs, see refund credit in ledger
8. Run tests to show concurrency handling

## Next: Deploy to Railway

After local testing works, follow [DEPLOYMENT.md](./DEPLOYMENT.md) for Railway setup.
