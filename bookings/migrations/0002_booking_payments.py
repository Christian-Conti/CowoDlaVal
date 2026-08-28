from decimal import Decimal
import uuid

import bookings.models
from django.db import migrations, models
import django.db.models.deletion


def backfill_booking_codes(apps, schema_editor):
    Booking = apps.get_model("bookings", "Booking")
    for booking in Booking.objects.order_by("pk").iterator():
        year = booking.created_at.year if booking.created_at else booking.date.year
        booking.booking_code = f"COWO-{year}-{booking.pk:06d}"
        booking.save(update_fields=["booking_code"])


class Migration(migrations.Migration):
    dependencies = [("bookings", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("8.00"), max_digits=8),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="booking",
            name="booking_code",
            field=models.CharField(max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="confirmation_sent_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="currency",
            field=models.CharField(default="EUR", editable=False, max_length=3),
        ),
        migrations.AddField(
            model_name="booking",
            name="language",
            field=models.CharField(default="it", max_length=10),
        ),
        migrations.AddField(
            model_name="booking",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="payment_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Not selected"),
                    ("onsite", "Pay in person"),
                    ("satispay", "Satispay"),
                    ("paypal", "PayPal"),
                    ("stripe", "Credit/debit card"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("unpaid", "Unpaid"),
                    ("pending", "Pending"),
                    ("paid", "Paid"),
                    ("failed", "Failed"),
                    ("refunded", "Refunded"),
                    ("cancelled", "Cancelled"),
                ],
                default="unpaid",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="tariff_category",
            field=models.CharField(
                choices=[("standard", "Standard"), ("discounted", "Student / resident")],
                default="standard",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_booking_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="booking",
            name="booking_code",
            field=models.CharField(
                default=bookings.models.generate_booking_code,
                editable=False,
                max_length=32,
                unique=True,
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["payment_method", "payment_status"], name="bookings_payment_idx"),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gte", 0)), name="booking_amount_nonnegative"),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("satispay", "Satispay"), ("paypal", "PayPal"), ("stripe", "Credit/debit card")], max_length=20)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed"), ("refunded", "Refunded"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=8)),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("idempotency_key", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("checkout_id", models.CharField(blank=True, max_length=255)),
                ("transaction_id", models.CharField(blank=True, max_length=255)),
                ("provider_status", models.CharField(blank=True, max_length=64)),
                ("provider_metadata", models.JSONField(blank=True, default=dict)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="bookings.booking")),
            ],
            options={
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("external_id", ""), _negated=True), fields=("provider", "external_id"), name="unique_provider_external_payment"),
                    models.UniqueConstraint(condition=models.Q(("checkout_id", ""), _negated=True), fields=("provider", "checkout_id"), name="unique_provider_checkout"),
                    models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="payment_amount_positive"),
                ],
            },
        ),
    ]
