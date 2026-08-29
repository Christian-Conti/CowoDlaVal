import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
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
                ("title_it", models.CharField(blank=True, max_length=180)),
                ("title_en", models.CharField(blank=True, max_length=180)),
                ("title_de", models.CharField(blank=True, max_length=180)),
                ("title_fr", models.CharField(blank=True, max_length=180)),
                ("short_description_it", models.CharField(blank=True, max_length=320)),
                ("short_description_en", models.CharField(blank=True, max_length=320)),
                ("short_description_de", models.CharField(blank=True, max_length=320)),
                ("short_description_fr", models.CharField(blank=True, max_length=320)),
                ("description_it", models.TextField(blank=True)),
                ("description_en", models.TextField(blank=True)),
                ("description_de", models.TextField(blank=True)),
                ("description_fr", models.TextField(blank=True)),
                ("date", models.DateField(db_index=True)),
                ("time", models.TimeField(blank=True, null=True)),
                ("location", models.CharField(blank=True, max_length=220)),
                ("is_public", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("date", "time", "pk")},
        ),
        migrations.CreateModel(
            name="EventImage",
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
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=100)),
                ("data", models.BinaryField(editable=False)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="events.event",
                    ),
                ),
            ],
            options={"ordering": ("position", "pk")},
        ),
    ]
