#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate
python manage.py seed_demo_data

celery -A payout_engine worker -l info --concurrency=1 &
worker_pid=$!

celery -A payout_engine beat -l info --schedule=/tmp/celerybeat-schedule &
beat_pid=$!

python -m gunicorn payout_engine.wsgi:application --bind "0.0.0.0:${PORT:-8000}" &
web_pid=$!

cleanup() {
  kill "$worker_pid" "$beat_pid" "$web_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait -n "$worker_pid" "$beat_pid" "$web_pid"
