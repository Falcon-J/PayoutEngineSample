import random
from dataclasses import dataclass
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import BigIntegerField, Case, F, Q, Sum, Value, When
from django.utils import timezone

from .models import IdempotencyRecord, LedgerEntry, Merchant, Payout


class ServiceError(Exception):
    pass


class InsufficientBalance(ServiceError):
    pass


class MissingIdempotencyKey(ServiceError):
    pass


class InvalidStateTransition(ServiceError):
    pass


@dataclass
class PayoutCreationResult:
    payout: Payout
    created: bool


@dataclass
class MerchantBalanceSnapshot:
    available_balance_paise: int
    held_balance_paise: int


def compute_balance_paise(merchant_id: int) -> int:
    total = (
        LedgerEntry.objects.filter(merchant_id=merchant_id)
        .aggregate(
            net=Sum(
                Case(
                    When(entry_type=LedgerEntry.EntryType.CREDIT, then=F("amount_paise")),
                    When(entry_type=LedgerEntry.EntryType.DEBIT, then=-F("amount_paise")),
                    default=Value(0),
                    output_field=BigIntegerField(),
                )
            )
        )
        .get("net")
    )
    return int(total or 0)


def compute_held_balance_paise(merchant_id: int) -> int:
    held = (
        Payout.objects.filter(merchant_id=merchant_id, status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING])
        .aggregate(total=Sum("amount_paise"))
        .get("total")
    )
    return int(held or 0)


def get_merchant_balance_snapshot(merchant_id: int) -> MerchantBalanceSnapshot:
    return MerchantBalanceSnapshot(
        available_balance_paise=compute_balance_paise(merchant_id),
        held_balance_paise=compute_held_balance_paise(merchant_id),
    )


def create_payout(
    merchant_id: int,
    amount_paise: int,
    idempotency_key: str,
    bank_account_id: str,
) -> PayoutCreationResult:
    if not idempotency_key:
        raise MissingIdempotencyKey("Idempotency-Key header is required")
    if amount_paise <= 0:
        raise ServiceError("amount_paise must be positive")
    if not bank_account_id:
        raise ServiceError("bank_account_id is required")

    with transaction.atomic():
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)

        now = timezone.now()
        existing_record = IdempotencyRecord.objects.filter(merchant=merchant, key=idempotency_key).select_related("payout").first()
        if existing_record and existing_record.expires_at > now:
            return PayoutCreationResult(payout=existing_record.payout, created=False)
        if existing_record and existing_record.expires_at <= now:
            existing_record.delete()

        balance = compute_balance_paise(merchant.id)
        if balance < amount_paise:
            raise InsufficientBalance("insufficient balance")

        try:
            payout = Payout.objects.create(
                merchant=merchant,
                amount_paise=amount_paise,
                bank_account_id=bank_account_id,
                idempotency_key=idempotency_key,
                status=Payout.Status.PENDING,
            )
            IdempotencyRecord.objects.create(
                merchant=merchant,
                key=idempotency_key,
                payout=payout,
                expires_at=now + timedelta(hours=24),
            )
        except IntegrityError:
            record = IdempotencyRecord.objects.get(merchant=merchant, key=idempotency_key)
            return PayoutCreationResult(payout=record.payout, created=False)

        LedgerEntry.objects.create(
            merchant=merchant,
            payout=payout,
            entry_type=LedgerEntry.EntryType.DEBIT,
            kind=LedgerEntry.Kind.PAYOUT_DEBIT,
            amount_paise=amount_paise,
        )

        return PayoutCreationResult(payout=payout, created=True)


def mark_payout_processing(payout_id: int) -> Payout:
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        if payout.status != Payout.Status.PENDING:
            raise InvalidStateTransition("payout must be pending before processing")

        payout.status = Payout.Status.PROCESSING
        payout.attempts += 1
        payout.processing_started_at = timezone.now()
        payout.next_retry_at = None
        payout.save(update_fields=["status", "attempts", "processing_started_at", "next_retry_at", "updated_at"])
        return payout


def mark_payout_completed(payout_id: int) -> Payout:
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        if payout.status != Payout.Status.PROCESSING:
            raise InvalidStateTransition("payout must be processing before completed")

        payout.status = Payout.Status.COMPLETED
        payout.processing_started_at = None
        payout.next_retry_at = None
        payout.save(update_fields=["status", "processing_started_at", "next_retry_at", "updated_at"])
        return payout


def mark_payout_failed_with_refund(payout_id: int) -> Payout:
    with transaction.atomic():
        payout = Payout.objects.select_for_update().select_related("merchant").get(id=payout_id)
        if payout.status != Payout.Status.PROCESSING:
            raise InvalidStateTransition("payout must be processing before failed")

        payout.status = Payout.Status.FAILED
        payout.processing_started_at = None
        payout.next_retry_at = None
        payout.save(update_fields=["status", "processing_started_at", "next_retry_at", "updated_at"])

        LedgerEntry.objects.get_or_create(
            merchant=payout.merchant,
            payout=payout,
            kind=LedgerEntry.Kind.PAYOUT_REFUND,
            defaults={
                "entry_type": LedgerEntry.EntryType.CREDIT,
                "amount_paise": payout.amount_paise,
            },
        )
        return payout


def process_single_pending_payout(payout_id: int) -> None:
    try:
        payout = mark_payout_processing(payout_id)
    except InvalidStateTransition:
        return

    outcome = random.random()
    if outcome < 0.7:
        mark_payout_completed(payout.id)
    elif outcome < 0.9:
        mark_payout_failed_with_refund(payout.id)
    else:
        return


def process_pending_payouts(limit: int = 50) -> int:
    now = timezone.now()
    payout_ids = list(
        Payout.objects.filter(status=Payout.Status.PENDING)
        .filter(Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now))
        .order_by("created_at")
        .values_list("id", flat=True)[:limit]
    )
    for payout_id in payout_ids:
        process_single_pending_payout(payout_id)
    return len(payout_ids)


def retry_stuck_payouts(max_attempts: int = 3, timeout_seconds: int = 30, base_backoff_seconds: int = 30) -> int:
    cutoff = timezone.now() - timedelta(seconds=timeout_seconds)
    payout_ids = list(
        Payout.objects.filter(status=Payout.Status.PROCESSING, processing_started_at__lt=cutoff).values_list("id", flat=True)
    )

    handled = 0
    for payout_id in payout_ids:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != Payout.Status.PROCESSING:
                continue

            if payout.attempts >= max_attempts:
                payout.status = Payout.Status.FAILED
                payout.processing_started_at = None
                payout.next_retry_at = None
                payout.save(update_fields=["status", "processing_started_at", "next_retry_at", "updated_at"])
                LedgerEntry.objects.get_or_create(
                    merchant=payout.merchant,
                    payout=payout,
                    kind=LedgerEntry.Kind.PAYOUT_REFUND,
                    defaults={
                        "entry_type": LedgerEntry.EntryType.CREDIT,
                        "amount_paise": payout.amount_paise,
                    },
                )
            else:
                retry_delay = base_backoff_seconds * (2 ** max(payout.attempts - 1, 0))
                payout.status = Payout.Status.PENDING
                payout.processing_started_at = None
                payout.next_retry_at = timezone.now() + timedelta(seconds=retry_delay)
                payout.save(update_fields=["status", "processing_started_at", "next_retry_at", "updated_at"])

            handled += 1

    return handled
