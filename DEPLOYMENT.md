# Deployment Guide

This guide covers deploying the Playto Payout Engine to Railway or Render.

## Prerequisites

- GitHub account with repository pushed
- Railway or Render account
- PostgreSQL and Redis instances (or use platform-provided)

## Option 1: Deploy to Railway (Recommended)

### Step 1: Connect Repository

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Django app

### Step 2: Create Database

1. In Railway dashboard, click "+ Add Service" → "PostgreSQL"
2. Create instance (Railway provides credentials automatically)

### Step 3: Create Cache Service

1. Click "+ Add Service" → "Redis"
2. Create instance

### Step 4: Configure Environment Variables

In Railway project settings, add:

```
DJANGO_SETTINGS_MODULE=payout_engine.settings
DEBUG=0
POSTGRES_DB=railway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=[from Railway DB service]
POSTGRES_HOST=[Railway DB host]
POSTGRES_PORT=[Railway DB port]
REDIS_URL=[Railway Redis URL]
DJANGO_SECRET_KEY=[generate random 50-char string]
```

Railway auto-injects `DATABASE_URL` and `REDIS_URL` if you link services.

### Step 5: Set Build Command

```bash
cd backend && pip install -r requirements.txt && python manage.py migrate
```

### Step 6: Set Start Command

```bash
cd backend && python -m gunicorn payout_engine.wsgi:application
```

**Important:** You'll need to run Celery beat and worker separately or use APScheduler.

For now, simple fix:
- Add `APScheduler` to requirements.txt
- OR run migrations manually, then only start web server

### Step 7: Deploy Frontend

1. Go to Vercel [vercel.com](https://vercel.com)
2. Import your GitHub repo
3. Framework: **Vite**
4. Build command: `cd frontend && npm install && npm run build`
5. Output directory: `frontend/dist`
6. Environment variable: `VITE_API_URL=https://[your-railway-backend-url]/api/v1`

### Step 8: Seed Data

After first deploy:

```bash
# SSH into Railway container or use CLI
railway run python manage.py seed_demo_data
```

## Option 2: Deploy to Render

### Step 1: Create Web Service

1. Go to [render.com](https://render.com)
2. New → "Web Service"
3. Connect GitHub repo
4. Select branch

### Step 2: Configure Service

```
Name: playto-payout-backend
Environment: Python 3.11
Build Command: cd backend && pip install -r requirements.txt && python manage.py migrate
Start Command: cd backend && python -m gunicorn payout_engine.wsgi:application
```

### Step 3: Add Environment Variables

```
DJANGO_SETTINGS_MODULE=payout_engine.settings
DEBUG=0
DJANGO_SECRET_KEY=[random 50-char string]
POSTGRES_DB=payout
POSTGRES_USER=payout_user
POSTGRES_PASSWORD=[generate strong password]
POSTGRES_HOST=[your-postgres-host]
POSTGRES_PORT=5432
REDIS_URL=redis://[your-redis-host]:[port]
```

### Step 4: Create PostgreSQL

1. Render → PostgreSQL instance
2. Copy connection string
3. Use to populate env vars above

### Step 5: Create Redis

1. Render → Redis instance
2. Copy connection URL
3. Use as REDIS_URL env var

### Step 6: Seed Data

```bash
render exec playto-payout-backend -- python manage.py seed_demo_data
```

### Step 7: Deploy Frontend to Vercel

Same as Railway option.

## Handling Celery Tasks

**Issue:** Celery Beat (periodic task scheduler) needs to run continuously.

**Solutions:**

1. **APScheduler (Easiest for free tier):**
   - Replace Celery Beat with built-in Django APScheduler
   - Tasks run within web process
   - Simpler deployment, no extra services

2. **Separate Celery Worker Service:**
   - Add another Railway/Render service for Celery worker
   - Add another service for Celery Beat
   - Requires more setup but more robust

For this challenge, **Option 1 is recommended** to keep deployment simple on free tier.

## Testing Live Deployment

After deployment:

1. Get backend URL from Railway/Render dashboard
2. Get frontend URL from Vercel
3. Open frontend in browser
4. Test merchant 1: Create payout with amount 600 INR
5. Verify with same idempotency key → should return same payout
6. Watch balance updates as payouts process

## Troubleshooting

### `ModuleNotFoundError: No module named 'django'`
- Ensure `requirements.txt` in `backend/` folder
- Build command includes `pip install -r requirements.txt`

### `ProgrammingError: relation "core_merchant" does not exist`
- Run migrations manually via CLI
- Or check build command runs `python manage.py migrate`

### Celery tasks not running
- Background tasks won't run on free tier without worker
- Frontend will still work, payouts stuck in `pending` forever
- Consider upgrading to paid tier for worker service, or implement APScheduler

### Redis connection refused
- Ensure REDIS_URL is correct
- Check Redis service is running on platform
- Verify firewall/network settings

## Performance Notes

- First request slower (cold start on free tier)
- Payouts won't auto-process without Celery Beat
- Manual testing: create payout, wait 5-10s, refresh page
- In production, add dedicated worker service

## Security Checklist

- [ ] `DEBUG=0` in production
- [ ] `DJANGO_SECRET_KEY` is random 50+ char string
- [ ] Database password is strong (20+ chars, mixed)
- [ ] Redis URL uses auth token if available
- [ ] CORS headers configured if frontend on different domain
- [ ] ALLOWED_HOSTS includes your domains in settings
