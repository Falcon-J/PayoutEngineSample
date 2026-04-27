from django.core.management.base import BaseCommand

from core.models import LedgerEntry, Merchant


class Command(BaseCommand):
    help = "Seed 3 merchants with deterministic credit history for demo/testing."

    def handle(self, *args, **options):
        merchants = [
            ("Alpha Agency", [200_000, 80_000]),
            ("Beta Studio", [150_000, 50_000]),
            ("Gamma Freelance", [90_000, 30_000]),
        ]

        created_count = 0
        for name, credits in merchants:
            merchant, _ = Merchant.objects.get_or_create(name=name)
            for amount in credits:
                _, created = LedgerEntry.objects.get_or_create(
                    merchant=merchant,
                    kind=LedgerEntry.Kind.MANUAL_CREDIT,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                    amount_paise=amount,
                )
                if created:
                    created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seed complete. Created {created_count} credit entries."))
