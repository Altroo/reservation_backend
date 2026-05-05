# Generated for Hilton residence interval reports.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("reservation", "0014_cost_building"),
    ]

    operations = [
        migrations.CreateModel(
            name="HiltonReport",
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
                ("start_date", models.DateField(db_index=True, verbose_name="Date début")),
                ("end_date", models.DateField(db_index=True, verbose_name="Date fin")),
                ("notes", models.TextField(blank=True, default="", verbose_name="Notes")),
                (
                    "gross_revenue",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Revenu brut",
                    ),
                ),
                (
                    "manual_cost_total",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Total coûts manuels",
                    ),
                ),
                (
                    "manual_adjustment_total",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Total ajustements manuels",
                    ),
                ),
                (
                    "net_total",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Total net",
                    ),
                ),
                (
                    "date_created",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        verbose_name="Date création",
                    ),
                ),
                (
                    "date_updated",
                    models.DateTimeField(auto_now=True, verbose_name="Date modification"),
                ),
                (
                    "created_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="hilton_reports_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Créé par",
                    ),
                ),
            ],
            options={
                "verbose_name": "Rapport Hilton",
                "verbose_name_plural": "Rapports Hilton",
                "ordering": ("-end_date", "-id"),
                "indexes": [
                    models.Index(
                        fields=["start_date", "end_date"],
                        name="hilton_report_dates_idx",
                    ),
                    models.Index(
                        fields=["end_date", "id"],
                        name="hilton_report_end_id_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="HiltonReportApartmentRevenue",
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
                    "apartment_nom",
                    models.CharField(max_length=100, verbose_name="Appartement"),
                ),
                (
                    "reservation_count",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Nombre de réservations"
                    ),
                ),
                (
                    "total_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Montant total",
                    ),
                ),
                (
                    "apartment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="reservation.apartment",
                        verbose_name="Appartement",
                    ),
                ),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="apartment_revenues",
                        to="reservation.hiltonreport",
                        verbose_name="Rapport",
                    ),
                ),
            ],
            options={
                "verbose_name": "Revenu appartement rapport Hilton",
                "verbose_name_plural": "Revenus appartements rapports Hilton",
                "ordering": ("apartment_nom", "id"),
            },
        ),
        migrations.CreateModel(
            name="HiltonReportManualLine",
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
                    "line_type",
                    models.CharField(
                        choices=[
                            ("cost", "Coût"),
                            ("adjustment", "Ajustement"),
                            ("note", "Note"),
                        ],
                        default="cost",
                        max_length=20,
                        verbose_name="Type",
                    ),
                ),
                (
                    "description",
                    models.CharField(max_length=300, verbose_name="Description"),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Montant",
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Ordre")),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="manual_lines",
                        to="reservation.hiltonreport",
                        verbose_name="Rapport",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ligne manuelle rapport Hilton",
                "verbose_name_plural": "Lignes manuelles rapports Hilton",
                "ordering": ("sort_order", "id"),
            },
        ),
    ]
