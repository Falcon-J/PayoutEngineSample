# Deployment Guide

This guide covers a production-style deployment for the Playto Payout Engine.

## Architecture

- Backend web service: Django + Gunicorn
- Database: PostgreSQL
- Queue and broker: Redis
- Async worker: Celery worker
- Scheduler: Celery beat
- Frontend: Vite static build

This repo needs all five runtime pieces if you want payouts to move from `pending` to `processing` to `completed` or `failed` automatically.

## Required Environment Variables

Set these for every backend process: web, worker, and beat.

```env
DJANGO_SETTINGS_MODULE=payout_engine.settings
DJANGO_SECRET_KEY=replace-with-a-random-secret
DEBUG=0
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_HOST=...
POSTGRES_PORT=5432
REDIS_URL=redis://...
ALLOWED_HOSTS=your-backend-domain
CORS_ALLOWED_ORIGINS=https://your-frontend-domain
CSRF_TRUSTED_ORIGINS=https://your-frontend-domain
```

For the frontend build:

```env
VITE_API_URL=https://your-backend-domain/api/v1
```

## Option 1: Railway + Vercel

### Free Railway shortcut

If your Railway account cannot create separate web, worker, and beat services, deploy a single Railway service using the bundled free-tier start script.

This runs Django, Celery worker, and Celery beat in one container. It is acceptable for the challenge demo because Celery is still doing the background processing; it is not the topology to use for a real production payment system.

Use this Railway configuration:

```bash
Build: cd backend && pip install -r requirements.txt
Start: cd backend && bash start_railway_free.sh
```

You still need PostgreSQL and Redis. If Railway will not let you create database services, use Neon or Supabase for PostgreSQL and Upstash for Redis, then paste their connection values into Railway variables.

### Railway backend

1. Push the repo to GitHub.
2. In Railway, create a new project from the repo.
3. Add a PostgreSQL service.
4. Add a Redis service.
5. Create a web service from the same repo with:

```bash
Build: cd backend && pip install -r requirements.txt && python manage.py migrate
Start: cd backend && python -m gunicorn payout_engine.wsgi:application --bind 0.0.0.0:$PORT
```

6. Set the backend environment variables listed above.
7. Create a worker service from the same repo with:

```bash
Build: cd backend && pip install -r requirements.txt
Start: cd backend && celery -A payout_engine worker -l info
```

8. Create a beat service from the same repo with:

```bash
Build: cd backend && pip install -r requirements.txt
Start: cd backend && celery -A payout_engine beat -l info
```

9. Seed demo data after first successful deploy:

```bash
railway run --service <web-service-name> sh -lc "cd backend && python manage.py seed_demo_data"
```

### Vercel frontend

1. Import the same repo into Vercel.
2. Set root directory to `frontend`.
3. Set build command to `npm run build`.
4. Set output directory to `dist`.
5. Set `VITE_API_URL=https://<your-railway-backend-domain>/api/v1`.
6. Deploy.

### Connect frontend and backend correctly

Use this rule: the frontend points to the backend API base, and the backend explicitly trusts the frontend origin.

Example production values:

```env
# Backend service variables
DEBUG=0
DJANGO_DEBUG=0
ALLOWED_HOSTS=your-backend.up.railway.app
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-frontend.vercel.app

# Frontend build variable
VITE_API_URL=https://your-backend.up.railway.app/api/v1
```

Important details:

- `VITE_API_URL` is read at frontend build time. If you change it in Vercel, redeploy the frontend.
- `VITE_API_URL` must include `/api/v1`.
- `ALLOWED_HOSTS` must contain only the backend hostname, without `https://`.
- `CORS_ALLOWED_ORIGINS` must contain the full frontend origin, including `https://`.
- Do not put a trailing slash in `VITE_API_URL`; the frontend removes one if present, but keeping it exact avoids confusion.

Run this backend smoke test before opening the frontend:

```powershell
.\scripts\smoke_deployment.ps1 -ApiBaseUrl "https://your-backend.up.railway.app/api/v1" -MerchantId 1
```

Expected result: balance, payouts, and ledger endpoints return JSON and the script prints `Deployment smoke test passed`.

Then verify from the deployed frontend:

1. Open the browser developer tools Network tab.
2. Reload the frontend.
3. Confirm requests go to `https://your-backend.../api/v1/balance`, `/payouts`, and `/ledger?limit=10`.
4. Confirm there are no CORS errors and no `400 DisallowedHost` responses.
5. Create a payout with a new idempotency key, then submit the same key again and confirm it replays the existing payout.

### Post-deploy verification

1. Open the frontend.
2. Use merchant `1`.
3. Create a payout with a fresh idempotency key.
4. Repeat the same request with the same key and confirm it replays instead of creating a second payout.
5. Wait 10-20 seconds and confirm the status changes from `pending`.
6. If a payout fails, confirm the refund appears in the ledger.

## Option 2: Render + Vercel

### Render backend

1. Create a PostgreSQL instance.
2. Create a Redis instance.
3. Create a web service from the repo:

```bash
Build: cd backend && pip install -r requirements.txt && python manage.py migrate
Start: cd backend && python -m gunicorn payout_engine.wsgi:application --bind 0.0.0.0:$PORT
```

4. Add the same backend environment variables.
5. Create a background worker service:

```bash
Build: cd backend && pip install -r requirements.txt
Start: cd backend && celery -A payout_engine worker -l info
```

6. Create another background worker service for beat:

```bash
Build: cd backend && pip install -r requirements.txt
Start: cd backend && celery -A payout_engine beat -l info
```

7. Seed demo data:

```bash
render exec <web-service-name> -- sh -lc "cd backend && python manage.py seed_demo_data"
```

### Vercel frontend

Use the same frontend steps as Railway, but point `VITE_API_URL` at the Render backend URL.

## Local-to-Prod Mapping

- Local `docker-compose.yml` gives you PostgreSQL and Redis.
- Local Django `runserver` becomes Gunicorn in production.
- Local Celery worker still exists in production as its own service.
- Local Celery beat still exists in production as its own service.
- Local Vite dev server proxy becomes `VITE_API_URL` in production.

## Exact Service Commands

### Local backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
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
python manage.py runserver
```

### Local worker

```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:POSTGRES_DB="payout"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:REDIS_URL="redis://localhost:6379/0"
$env:DJANGO_SETTINGS_MODULE="payout_engine.settings"
celery -A payout_engine worker -l info
```

### Local beat

```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:POSTGRES_DB="payout"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:REDIS_URL="redis://localhost:6379/0"
$env:DJANGO_SETTINGS_MODULE="payout_engine.settings"
celery -A payout_engine beat -l info
```

### Local frontend

```powershell
cd frontend
npm install
npm run dev
```

## Common Failure Modes

### Frontend loads but API calls fail

- `VITE_API_URL` is missing or wrong for production.
- Backend domain is not included in `ALLOWED_HOSTS`.
- Frontend domain is not included in `CORS_ALLOWED_ORIGINS`.

### Payouts stay `pending`

- Celery worker is not running.
- Celery beat is not running.
- `REDIS_URL` differs between services.

### Backend deploys but crashes on start

- `gunicorn` was not installed from `backend/requirements.txt`.
- The service started from repo root instead of `backend`.
- Required PostgreSQL env vars are missing.
- PostgreSQL driver dependencies were not installed. `backend/requirements.txt` must include `psycopg[binary]`; if you build a custom Debian/Ubuntu Docker image, install `libpq5` in the runtime image.

For a custom Debian/Ubuntu backend Dockerfile:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
```

For a custom Alpine backend Dockerfile:

```dockerfile
RUN apk add --no-cache postgresql-libs
```

### Seed command fails

- Migrations did not run.
- The seed command was executed from the repo root instead of `backend`.

## Production Checklist

- `DEBUG=0`
- Strong `DJANGO_SECRET_KEY`
- Real backend hostname in `ALLOWED_HOSTS`
- Real frontend origin in `CORS_ALLOWED_ORIGINS`
- Web service deployed
- Worker service deployed
- Beat service deployed
- Migrations executed
- Demo data seeded
- Frontend `VITE_API_URL` points to `/api/v1`
