from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="payout",
            name="uniq_merchant_idempotency_key",
        ),
        migrations.AddField(
            model_name="payout",
            name="bank_account_id",
            field=models.CharField(default="bank_demo", max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="payout",
            name="next_retry_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="IdempotencyRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="idempotency_records",
                        to="core.merchant",
                    ),
                ),
                (
                    "payout",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="idempotency_records",
                        to="core.payout",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="idempotencyrecord",
            constraint=models.UniqueConstraint(
                fields=("merchant", "key"),
                name="uniq_merchant_idempotency_key_record",
            ),
        ),
    ]
