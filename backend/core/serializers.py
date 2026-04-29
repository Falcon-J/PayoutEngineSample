from django.utils import timezone
from rest_framework import serializers

from .models import LedgerEntry, Payout


class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=128)


class MerchantCreditSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            "id",
            "amount_paise",
            "bank_account_id",
            "status",
            "idempotency_key",
            "attempts",
            "created_at",
            "updated_at",
        ]


class BalanceSerializer(serializers.Serializer):
    available_balance_paise = serializers.IntegerField()
    held_balance_paise = serializers.IntegerField()
    as_of = serializers.DateTimeField(default=timezone.now)


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ["id", "entry_type", "kind", "amount_paise", "payout_id", "created_at"]
