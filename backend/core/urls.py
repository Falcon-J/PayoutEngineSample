from django.urls import path

from .views import BalanceView, LedgerListView, PayoutListCreateView, demo_page, healthz

urlpatterns = [
    path("", demo_page, name="demo"),
    path("healthz", healthz, name="healthz"),
    path("api/v1/balance", BalanceView.as_view(), name="api-v1-balance"),
    path("api/v1/payouts", PayoutListCreateView.as_view(), name="api-v1-payouts"),
    path("api/v1/ledger", LedgerListView.as_view(), name="api-v1-ledger"),
    path("api/balance", BalanceView.as_view(), name="api-balance"),
    path("api/payouts", PayoutListCreateView.as_view(), name="api-payouts"),
    path("api/ledger", LedgerListView.as_view(), name="api-ledger"),
    path("balance", BalanceView.as_view(), name="balance"),
    path("payouts", PayoutListCreateView.as_view(), name="payouts"),
]
