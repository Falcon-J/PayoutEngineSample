from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError

from core.models import LedgerEntry, Merchant


class Command(BaseCommand):
    help = "Add manual credit to a merchant ledger for demo or operational testing."

    def add_arguments(self, parser):
        parser.add_argument("--merchant-id", type=int, required=True, help="Merchant id to credit.")
        parser.add_argument("--amount-inr", help="Credit amount in INR, for example 5000.00.")
        parser.add_argument("--amount-paise", type=int, help="Credit amount in paise.")

    def handle(self, *args, **options):
        amount_inr = options.get("amount_inr")
        amount_paise = options.get("amount_paise")

        if amount_inr is None and amount_paise is None:
            raise CommandError("Provide either --amount-inr or --amount-paise.")
        if amount_inr is not None and amount_paise is not None:
            raise CommandError("Provide only one amount option: --amount-inr or --amount-paise.")

        if amount_inr is not None:
            amount_paise = self.parse_inr_to_paise(amount_inr)

        if amount_paise <= 0:
            raise CommandError("Credit amount must be greater than zero.")

        try:
            merchant = Merchant.objects.get(id=options["merchant_id"])
        except Merchant.DoesNotExist as exc:
            raise CommandError(f"Merchant {options['merchant_id']} does not exist.") from exc

        entry = LedgerEntry.objects.create(
            merchant=merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            kind=LedgerEntry.Kind.MANUAL_CREDIT,
            amount_paise=amount_paise,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Credited merchant {merchant.id} ({merchant.name}) with INR {amount_paise / 100:.2f}. "
                f"Ledger entry id: {entry.id}."
            )
        )

    @staticmethod
    def parse_inr_to_paise(value: str) -> int:
        try:
            amount = Decimal(value.replace(",", "").strip())
        except (AttributeError, InvalidOperation) as exc:
            raise CommandError("--amount-inr must be a valid decimal amount.") from exc

        paise = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(paise)
