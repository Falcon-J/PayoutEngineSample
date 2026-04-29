from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LedgerEntry, Merchant, Payout
from .serializers import BalanceSerializer, LedgerEntrySerializer, PayoutCreateSerializer, PayoutSerializer
from .services import (
    InsufficientBalance,
    MissingIdempotencyKey,
    ServiceError,
    create_payout,
    get_merchant_balance_snapshot,
)


def healthz(request):
    return JsonResponse({"status": "ok", "service": "payout-engine"})


def demo_page(request):
    return render(request, "demo.html")


class MerchantHeaderMixin:
    def get_merchant(self, request):
        merchant_id = request.headers.get("X-Merchant-Id")
        if not merchant_id:
            return None, Response({"detail": "X-Merchant-Id header is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not merchant_id.isdigit():
            return None, Response({"detail": "X-Merchant-Id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
        merchant = get_object_or_404(Merchant, id=int(merchant_id))
        return merchant, None


class BalanceView(MerchantHeaderMixin, APIView):
    def get(self, request):
        merchant, error = self.get_merchant(request)
        if error:
            return error

        snapshot = get_merchant_balance_snapshot(merchant.id)
        serializer = BalanceSerializer(
            {
                "available_balance_paise": snapshot.available_balance_paise,
                "held_balance_paise": snapshot.held_balance_paise,
            }
        )
        return Response(serializer.data)


class PayoutListCreateView(MerchantHeaderMixin, APIView):
    def get(self, request):
        merchant, error = self.get_merchant(request)
        if error:
            return error

        payouts = Payout.objects.filter(merchant=merchant).order_by("-created_at")
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)

    def post(self, request):
        merchant, error = self.get_merchant(request)
        if error:
            return error

        serializer = PayoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idempotency_key = request.headers.get("Idempotency-Key")
        try:
            result = create_payout(
                merchant_id=merchant.id,
                amount_paise=serializer.validated_data["amount_paise"],
                idempotency_key=idempotency_key or "",
                bank_account_id=serializer.validated_data["bank_account_id"],
            )
        except MissingIdempotencyKey as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except InsufficientBalance as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        output = PayoutSerializer(result.payout)
        response_status = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        return Response(output.data, status=response_status)


class LedgerListView(MerchantHeaderMixin, APIView):
    def get(self, request):
        merchant, error = self.get_merchant(request)
        if error:
            return error

        limit_raw = request.query_params.get("limit", "20")
        limit = int(limit_raw) if limit_raw.isdigit() else 20
        limit = max(1, min(limit, 100))

        entries = LedgerEntry.objects.filter(merchant=merchant).order_by("-created_at")[:limit]
        serializer = LedgerEntrySerializer(entries, many=True)
        return Response(serializer.data)
