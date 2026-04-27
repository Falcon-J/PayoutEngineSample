from django.db import models
from django.db.models import Q


class Merchant(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="payouts")
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=128)
    idempotency_key = models.CharField(max_length=128)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    attempts = models.IntegerField(default=0)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount_paise__gt=0), name="payout_amount_positive"),
            models.CheckConstraint(condition=Q(attempts__gte=0), name="payout_attempts_non_negative"),
        ]


class IdempotencyRecord(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="idempotency_records")
    key = models.CharField(max_length=128)
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name="idempotency_records")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["merchant", "key"], name="uniq_merchant_idempotency_key_record"),
        ]


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Kind(models.TextChoices):
        PAYOUT_DEBIT = "payout_debit", "Payout Debit"
        PAYOUT_REFUND = "payout_refund", "Payout Refund"
        MANUAL_CREDIT = "manual_credit", "Manual Credit"

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="ledger_entries")
    payout = models.ForeignKey(Payout, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries")
    entry_type = models.CharField(max_length=16, choices=EntryType.choices)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    amount_paise = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount_paise__gt=0), name="ledger_amount_positive"),
            models.UniqueConstraint(
                fields=["payout", "kind"],
                condition=Q(kind="payout_refund"),
                name="uniq_single_refund_per_payout",
            ),
            models.UniqueConstraint(
                fields=["payout", "kind"],
                condition=Q(kind="payout_debit"),
                name="uniq_single_debit_per_payout",
            ),
        ]
