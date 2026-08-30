from django.db import migrations


INDEX_NAME = "auth_user_email_ci_unique"


def normalise_and_check_emails(apps, schema_editor):
    User = apps.get_model("auth", "User")

    normalised = {}
    updates = []
    duplicates = []

    for user in User.objects.exclude(email="").only("id", "email").iterator():
        email = user.email.strip().lower()
        if user.email != email:
            user.email = email
            updates.append(user)

        if not email:
            continue

        previous_user_id = normalised.get(email)
        if previous_user_id is not None:
            duplicates.append((email, previous_user_id, user.pk))
            continue

        normalised[email] = user.pk

    if duplicates:
        details = ", ".join(
            f"{email} (users {first_id} and {second_id})"
            for email, first_id, second_id in duplicates[:10]
        )
        raise RuntimeError(
            "Cannot enforce case-insensitive unique email addresses because "
            f"duplicates already exist: {details}"
        )

    if updates:
        User.objects.bulk_update(updates, ["email"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(
            normalise_and_check_emails,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql=(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{INDEX_NAME}" '
                'ON "auth_user" (LOWER("email")) WHERE "email" <> \'\';'
            ),
            reverse_sql=f'DROP INDEX IF EXISTS "{INDEX_NAME}";',
        ),
    ]
