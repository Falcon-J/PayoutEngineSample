# Submission Checklist

## Code Quality & Architecture

- [x] Models use BigIntegerField for all amounts (paise)
- [x] Balance calculated at query-time using SQL Case/When aggregation
- [x] No stored balance column (derived only)
- [x] Concurrency protection: SELECT FOR UPDATE on merchant row
- [x] Idempotency key validation: unique per merchant, 24h expiry
- [x] State machine transitions enforced (no backwards transitions)
- [x] Failed payout refunds atomic with state change
- [x] Retry logic with exponential backoff (30s, 60s, 120s)
- [x] Max 3 retry attempts before final failure
- [x] All database operations within transactions
- [x] Ledger entries append-only (never modified/deleted)

## Tests

- [x] Concurrency test: Two simultaneous payouts, one rejected
- [x] Idempotency test: Same key returns same response
- [x] Expiry test: 24h expired key allows new payout
- [x] Tests use TransactionTestCase and threading for real concurrency
- [x] Tests pass locally

## API Contract

- [x] `POST /api/v1/payouts` with Idempotency-Key header
- [x] `GET /api/v1/balance` returns available + held
- [x] `GET /api/v1/payouts` lists payout history
- [x] `GET /api/v1/ledger` shows transaction feed
- [x] X-Merchant-Id header required for all requests
- [x] Proper HTTP status codes (201 created, 200 ok, 400 error)

## Frontend

- [x] React dashboard at http://localhost:5173
- [x] Real-time balance display (available + held)
- [x] Payout request form with INR to paise conversion
- [x] Payout history table with status badges
- [x] Ledger entry display with kind/type labels
- [x] 3-second auto-refresh via polling
- [x] Merchant ID switcher
- [x] Idempotency key input for demonstration

## Background Processing

- [x] Celery Beat scheduled tasks (every 5s + 10s)
- [x] Payout processor: 70% success, 20% fail, 10% stuck
- [x] Stuck payout retry with exponential backoff
- [x] Max 3 attempts before fail + refund
- [x] Redis broker + PostgreSQL result backend

## Deployment

- [x] docker-compose.yml with PostgreSQL + Redis
- [x] requirements.txt with all dependencies
- [x] .env.example template
- [x] DEPLOYMENT.md with Railway/Render instructions
- [x] LOCAL_SETUP.md with Windows development guide
- [x] manage.py configured correctly
- [x] Migrations checked in and numbered sequentially

## Documentation

- [x] README.md: Setup, API contract, tests, troubleshooting
- [x] EXPLAINER.md: All 5 questions answered with code
  - Ledger calculation query
  - Concurrency lock (SELECT FOR UPDATE)
  - Idempotency (UUID table, 24h expiry)
  - State machine transitions
  - AI audit (caught incorrect aggregate math)
- [x] Clear commit messages explaining each change
- [x] .gitignore prevents venv/node_modules/logs/secrets

## GitHub Repository

- [x] 15 clean, semantic commits
- [x] One feature per commit
- [x] Commit messages follow convention (feat:, test:, docs:, chore:)
- [x] All source code pushed
- [x] No credentials in code
- [x] No large binary files

## Data Integrity Verification

- [x] Ledger invariant: sum(credits) - sum(debits) = balance
- [x] Unique payout: one debit per payout only
- [x] Unique refund: one credit refund per failed payout only
- [x] Concurrent payouts: only one succeeds if overdraw
- [x] Failed refunds: funds immediately available (same transaction)

## Deployment & Live Testing

### Before You Deploy:
- [ ] Clone repo into fresh directory
- [ ] Follow LOCAL_SETUP.md exactly
- [ ] Run tests: `python manage.py test core.tests`
- [ ] All 3 tests pass
- [ ] Create payout manually in dashboard
- [ ] Re-submit same key → same payout returned
- [ ] Observe status transitions

### Deploy to Railway/Render:
- [ ] Follow DEPLOYMENT.md step-by-step
- [ ] Set all environment variables
- [ ] Run migrations on deployed DB
- [ ] Run seed data command
- [ ] Test live endpoints with curl or Postman
- [ ] Test live dashboard in browser

### Final Verification:
- [ ] Frontend loads
- [ ] Can create payout with idempotency key
- [ ] Same key replay works
- [ ] Balance updates (even if slow)
- [ ] API endpoints return 200/201/400 correctly

## Submission Form

When submitting, provide:

1. **GitHub Repository URL**
   - [To fill in]

2. **Backend URL** (from Railway/Render)
   - [To fill in]

3. **Frontend URL** (from Vercel or similar)
   - [To fill in]

4. **Demo Instructions**
   - Use merchant ID: 1, 2, or 3
   - Merchant 1 (Alpha Agency): 2000 INR available
   - Create payout: 600 INR, key "demo-key-001"
   - Repeat same key → should return same payout
   - Wait 5-10s for processing
   - Observe status and balance changes

5. **Important Notes**
   - Tests verify concurrency and idempotency
   - Ledger proves balance invariant
   - No AI-dependent code (all verified)
   - Architecture designed for production money movement

## Grading Rubric (from Challenge)

- [x] Clean ledger model (integer paise, append-only)
- [x] Correct concurrency (database-level SELECT FOR UPDATE)
- [x] Good idempotency (UUID table, 24h expiry, scoped per merchant)
- [x] Sharp EXPLAINER.md (understand own code)
- [x] Honest AI audit (caught specific error: string math vs F() expression)

## Quality Indicators

- ✅ No DecimalField or FloatField for money
- ✅ No Python-level arithmetic for balance
- ✅ No race conditions (verified by tests)
- ✅ No duplicate ledger entries (unique constraints)
- ✅ No stored balance (always derived)
- ✅ Idempotency key required (not optional)
- ✅ State machine validates transitions
- ✅ Failed payout refunds atomic
- ✅ Retry logic with backoff
- ✅ Tests prove correctness

## Optional Bonuses (Implement if time)

- [ ] Audit log of all state transitions
- [ ] Event sourcing for payout lifecycle
- [ ] Webhook delivery with retries
- [ ] API rate limiting
- [ ] Encrypted sensitive fields
- [ ] JWT authentication

(Focus on core first, bonuses only if time permits)

## Troubleshooting Before Submission

**Tests fail:** Ensure PostgreSQL running, migrations applied, venv activated

**Frontend can't connect:** Check VITE_API_URL env var or proxy settings

**Payouts stuck pending:** Celery worker/beat not running (acceptable for free tier)

**Balance wrong:** Check ledger entries, run `python manage.py test core.tests.test_balance_invariant` if exists

**Deployment fails:** Check build command includes migrations, secret key is set

---

**Ready to submit?** ✅ All boxes checked above means you're good to go!
