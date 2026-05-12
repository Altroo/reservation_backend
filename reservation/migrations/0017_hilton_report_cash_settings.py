# Generated for Hilton cash report settings and print fields.

from django.db import migrations, models


def create_hilton_report_settings(apps, schema_editor):
    HiltonReportSettings = apps.get_model("reservation", "HiltonReportSettings")
    HiltonReportSettings.objects.get_or_create(singleton_key=1)


class Migration(migrations.Migration):

    dependencies = [
        ("reservation", "0016_hiltonreport_airbnb_total_hiltonreport_bank_total_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="HiltonReportSettings",
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
                (
                    "singleton_key",
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "carry_forward_balance",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Balance à reporter",
                    ),
                ),
                (
                    "date_updated",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Date modification",
                    ),
                ),
            ],
            options={
                "verbose_name": "Paramètres rapport Hilton",
                "verbose_name_plural": "Paramètres rapport Hilton",
            },
        ),
        migrations.AddField(
            model_name="hiltonreport",
            name="opening_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name="Balance à reporter",
            ),
        ),
        migrations.AddField(
            model_name="hiltonreport",
            name="cash_register_total",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name="Caisse Hilton",
            ),
        ),
        migrations.AddField(
            model_name="hiltonreport",
            name="cost_period_label",
            field=models.CharField(
                blank=True,
                default="",
                max_length=120,
                verbose_name="Période des coûts",
            ),
        ),
        migrations.AddField(
            model_name="hiltonreportmanualline",
            name="operations_count",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Nombre d'opérations",
            ),
        ),
        migrations.RunPython(
            create_hilton_report_settings,
            migrations.RunPython.noop,
        ),
    ]
