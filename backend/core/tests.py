import threading
from datetime import timedelta

from django.core.management import call_command
from django.db import close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from django.utils import timezone

from .models import IdempotencyRecord, LedgerEntry, Merchant, Payout
from .services import InsufficientBalance, create_payout


class PayoutEngineTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.client = APIClient()
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            kind=LedgerEntry.Kind.MANUAL_CREDIT,
            amount_paise=10_000,
        )

    def test_idempotency_same_key_returns_same_payout(self):
        first = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=4_000,
            bank_account_id="bank_a",
            idempotency_key="idem-1",
        )
        second = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=4_000,
            bank_account_id="bank_a",
            idempotency_key="idem-1",
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.payout.id, second.payout.id)
        self.assertEqual(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                kind=LedgerEntry.Kind.PAYOUT_DEBIT,
            ).count(),
            1,
        )
        self.assertEqual(
            IdempotencyRecord.objects.filter(merchant=self.merchant, key="idem-1").count(),
            1,
        )

    def test_concurrent_overdraw_allows_only_one_payout(self):
        barrier = threading.Barrier(2)
        results = []
        lock = threading.Lock()

        def worker(key: str):
            close_old_connections()
            barrier.wait()
            try:
                result = create_payout(
                    merchant_id=self.merchant.id,
                    amount_paise=6_000,
                    bank_account_id="bank_a",
                    idempotency_key=key,
                )
                payload = ("created", result.payout.id)
            except InsufficientBalance:
                payload = ("insufficient", None)
            finally:
                close_old_connections()

            with lock:
                results.append(payload)

        t1 = threading.Thread(target=worker, args=("key-1",))
        t2 = threading.Thread(target=worker, args=("key-2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        created_count = sum(1 for status, _ in results if status == "created")
        insufficient_count = sum(1 for status, _ in results if status == "insufficient")

        self.assertEqual(created_count, 1)
        self.assertEqual(insufficient_count, 1)
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)
        self.assertEqual(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                kind=LedgerEntry.Kind.PAYOUT_DEBIT,
            ).count(),
            1,
        )

    def test_idempotency_key_expires_after_24_hours(self):
        first = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=1_000,
            bank_account_id="bank_a",
            idempotency_key="expiring-key",
        )
        record = IdempotencyRecord.objects.get(merchant=self.merchant, key="expiring-key")
        record.expires_at = timezone.now() - timedelta(seconds=1)
        record.save(update_fields=["expires_at"])

        second = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=1_000,
            bank_account_id="bank_a",
            idempotency_key="expiring-key",
        )

        self.assertTrue(first.created)
        self.assertTrue(second.created)
        self.assertNotEqual(first.payout.id, second.payout.id)

    def test_credit_merchant_command_adds_manual_credit(self):
        call_command("credit_merchant", merchant_id=self.merchant.id, amount_inr="123.45")

        self.assertTrue(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                entry_type=LedgerEntry.EntryType.CREDIT,
                kind=LedgerEntry.Kind.MANUAL_CREDIT,
                amount_paise=12_345,
            ).exists()
        )

    def test_credit_endpoint_adds_manual_credit(self):
        response = self.client.post(
            "/api/v1/credits",
            {"amount_paise": 50_000},
            format="json",
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                entry_type=LedgerEntry.EntryType.CREDIT,
                kind=LedgerEntry.Kind.MANUAL_CREDIT,
                amount_paise=50_000,
            ).exists()
        )
