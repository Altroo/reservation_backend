"""Simplify Apartment: keep only ``nom`` (migrated from ``code``)."""

from django.db import migrations, models


def migrate_code_to_nom(apps, schema_editor):
    """Copy existing ``code`` values into the new ``nom`` column."""
    Apartment = apps.get_model("reservation", "Apartment")
    for apt in Apartment.objects.all():
        apt.nom = apt.code
        apt.save(update_fields=["nom"])


class Migration(migrations.Migration):

    dependencies = [
        ("reservation", "0004_add_amount_returned"),
    ]

    operations = [
        # 1. Add the new ``nom`` field (nullable temporarily)
        migrations.AddField(
            model_name="apartment",
            name="nom",
            field=models.CharField(
                max_length=100,
                null=True,
                verbose_name="Nom de l'appartement",
                help_text="Nom de l'appartement",
            ),
        ),
        # 2. Copy data from code → nom
        migrations.RunPython(migrate_code_to_nom, migrations.RunPython.noop),
        # 3. Make nom non-null and unique
        migrations.AlterField(
            model_name="apartment",
            name="nom",
            field=models.CharField(
                max_length=100,
                unique=True,
                verbose_name="Nom de l'appartement",
                help_text="Nom de l'appartement",
            ),
        ),
        # 4. Remove old fields
        migrations.RemoveField(model_name="apartment", name="code"),
        migrations.RemoveField(model_name="apartment", name="name"),
        migrations.RemoveField(model_name="apartment", name="monthly_cost"),
        migrations.RemoveField(model_name="apartment", name="is_active"),
        # 5. Update Meta ordering
        migrations.AlterModelOptions(
            name="apartment",
            options={
                "ordering": ("nom",),
                "verbose_name": "Appartement",
                "verbose_name_plural": "Appartements",
            },
        ),
    ]
