# EXPLAINER

This document answers the five required questions in plain language and points to the exact implementation approach.

## 1) The Ledger

Balance is derived in SQL, not stored as a mutable column.

```python
LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
    net=Sum(
        Case(
            When(entry_type=LedgerEntry.EntryType.CREDIT, then=F("amount_paise")),
            When(entry_type=LedgerEntry.EntryType.DEBIT, then=-F("amount_paise")),
            default=Value(0),
            output_field=BigIntegerField(),
        )
    )
).get("net")
```

Why I modeled it this way:
- Ledger entries are append-only money events.
- Credits represent incoming funds.
- Debits represent payout holds/outflow.
- Refunds are compensating credits.
- This gives an auditable trail and avoids stale balance bugs.

Available vs held:
- Available balance = sum(credits) - sum(debits) from ledger.
- Held balance = sum(amount_paise) of payouts in pending or processing.
- In UI, both are shown so operator sees what can be withdrawn now vs what is in-flight.

## 2) The Lock

Exact overdraw prevention section:

```python
with transaction.atomic():
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)
    balance = compute_balance_paise(merchant.id)
    if balance < amount_paise:
        raise InsufficientBalance("insufficient balance")
    # create payout + debit ledger entry
```

Primitive used:
- Database row lock using SELECT FOR UPDATE.
- This serializes payout creation per merchant and prevents check-then-deduct race conditions.

## 3) The Idempotency

How the system knows a key was seen:
- Table: IdempotencyRecord.
- Unique constraint: (merchant, key).
- Record stores payout reference and expires_at.

Behavior:
- If same key is reused within 24 hours, return original payout response.
- If key is expired, delete stale record and allow fresh request.

In-flight race timeline:
1. Request A arrives with key K and enters transaction.
2. Request A locks merchant row and creates payout + idempotency record.
3. Request B with same key K arrives while A is in flight.
4. Request B waits on merchant row lock.
5. After A commits, B resumes and sees existing idempotency record.
6. B returns same payout (no duplicate ledger debit).

## 4) The State Machine

Legal transitions implemented:
- pending -> processing -> completed
- pending -> processing -> failed

Illegal transitions are blocked by service checks such as:

```python
if payout.status != Payout.Status.PROCESSING:
    raise InvalidStateTransition("payout must be processing before completed")
```

and

```python
if payout.status != Payout.Status.PROCESSING:
    raise InvalidStateTransition("payout must be processing before failed")
```

This rejects failed -> completed, completed -> pending, and any backward transition.

Atomic failure + refund:
- In the same transaction that sets status to failed, the refund ledger credit is inserted.
- So state and money movement stay consistent.

## 5) The AI Audit

One subtle incorrect suggestion from AI:

```python
When(entry_type=LedgerEntry.EntryType.DEBIT, then=-1 * "amount_paise")
```

Why this is wrong:
- It is string-level/Python-style arithmetic, not SQL field expression arithmetic.
- Can break correctness of aggregate math.

Fix I applied:

```python
When(entry_type=LedgerEntry.EntryType.DEBIT, then=-F("amount_paise"))
```

Why fix is correct:
- F(...) keeps arithmetic in database query execution.
- Balance invariant remains exact and auditable.

## Retry Timeline (for clarity)

For payouts stuck in processing longer than threshold:
1. Attempt 1 stuck -> moved back to pending with next_retry_at = now + 30s.
2. Attempt 2 stuck -> next_retry_at = now + 60s.
3. Attempt 3 stuck -> next_retry_at = now + 120s.
4. If max attempts reached -> failed + refund credit in same transaction.
