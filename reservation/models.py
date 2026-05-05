from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from account.models import CustomUser


class PaymentSourceOption(models.Model):
    """Available payment sources for reservation forms."""

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Source de paiement"),
    )

    class Meta:
        verbose_name = _("Source de paiement")
        verbose_name_plural = _("Sources de paiement")
        ordering = ("nom",)

    def __str__(self) -> str:
        return self.nom


class Apartment(models.Model):
    """Représente un appartement / unité louée."""

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Nom de l'appartement"),
        help_text=_("Nom de l'appartement"),
    )
    building = models.ForeignKey(
        "building.Building",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="apartments",
        verbose_name=_("Résidence"),
    )

    history = HistoricalRecords(
        verbose_name=_("Historique Appartement"),
        verbose_name_plural=_("Historiques Appartements"),
    )

    class Meta:
        verbose_name = _("Appartement")
        verbose_name_plural = _("Appartements")
        ordering = ("nom",)

    def __str__(self) -> str:
        return self.nom


class Reservation(models.Model):
    """Représente une réservation pour un appartement sur une date donnée."""

    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.PROTECT,
        related_name="reservations",
        verbose_name=_("Appartement"),
    )
    guest_name = models.CharField(
        max_length=200,
        verbose_name=_("Nom du client"),
        help_text=_("Nom complet du client"),
    )
    check_in = models.DateField(
        verbose_name=_("Date d'arrivée"),
        db_index=True,
    )
    check_out = models.DateField(
        verbose_name=_("Date de départ"),
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Montant (MAD)"),
        help_text=_("Montant total de la réservation en MAD"),
    )
    payment_source = models.CharField(
        max_length=50,
        default="Cash",
        verbose_name=_("Source de paiement"),
        db_index=True,
    )
    amount_returned = models.BooleanField(
        default=False,
        verbose_name=_("Montant retourné"),
        help_text=_("Indique si le montant a été retourné"),
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Notes"),
    )
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations_created",
        verbose_name=_("Créé par"),
    )
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date création"), db_index=True
    )
    date_updated = models.DateTimeField(
        auto_now=True, verbose_name=_("Date modification")
    )

    history = HistoricalRecords(
        verbose_name=_("Historique Réservation"),
        verbose_name_plural=_("Historiques Réservations"),
    )

    class Meta:
        verbose_name = _("Réservation")
        verbose_name_plural = _("Réservations")
        ordering = ("-check_in",)
        indexes = [
            models.Index(fields=["apartment", "check_in"]),
            models.Index(fields=["check_in", "check_out"]),
            models.Index(fields=["payment_source"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.guest_name} — {self.apartment} ({self.check_in} → {self.check_out})"
        )

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days


class Cost(models.Model):
    """Represents a cost entry (maintenance, charges, taxes, etc.)."""

    CATEGORY_CHOICES = [
        ("Entretien", _("Entretien")),
        ("Charges", _("Charges")),
        ("Assurance", _("Assurance")),
        ("Taxes", _("Taxes")),
        ("Autre", _("Autre")),
    ]

    description = models.CharField(
        max_length=300,
        verbose_name=_("Description"),
        help_text=_("Description du coût"),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Montant (MAD)"),
    )
    date = models.DateField(verbose_name=_("Date"), db_index=True)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="Autre",
        verbose_name=_("Catégorie"),
        db_index=True,
    )
    building = models.ForeignKey(
        "building.Building",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="costs",
        verbose_name=_("Résidence"),
    )
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="costs_created",
        verbose_name=_("Créé par"),
    )
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date création")
    )
    date_updated = models.DateTimeField(
        auto_now=True, verbose_name=_("Date modification")
    )
    history = HistoricalRecords(
        verbose_name=_("Historique Coût"),
        verbose_name_plural=_("Historiques Coûts"),
    )

    class Meta:
        verbose_name = _("Coût")
        verbose_name_plural = _("Coûts")
        ordering = ("-date",)

    def __str__(self) -> str:
        return f"{self.description} — {self.amount} MAD ({self.date})"


class HiltonReport(models.Model):
    """Saved interval report for Hilton residence revenue and manual lines."""

    start_date = models.DateField(verbose_name=_("Date début"), db_index=True)
    end_date = models.DateField(verbose_name=_("Date fin"), db_index=True)
    notes = models.TextField(blank=True, default="", verbose_name=_("Notes"))
    gross_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Revenu brut"),
    )
    manual_cost_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Total coûts manuels"),
    )
    manual_adjustment_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Total ajustements manuels"),
    )
    net_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Total net"),
    )
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hilton_reports_created",
        verbose_name=_("Créé par"),
    )
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date création"), db_index=True
    )
    date_updated = models.DateTimeField(
        auto_now=True, verbose_name=_("Date modification")
    )

    class Meta:
        verbose_name = _("Rapport Hilton")
        verbose_name_plural = _("Rapports Hilton")
        ordering = ("-end_date", "-id")
        indexes = [
            models.Index(fields=["start_date", "end_date"], name="hilton_report_dates_idx"),
            models.Index(fields=["end_date", "id"], name="hilton_report_end_id_idx"),
        ]

    def __str__(self) -> str:
        return f"Hilton residence — {self.start_date} / {self.end_date}"

    def recalculate_totals(self, save: bool = True) -> None:
        gross = (
            self.apartment_revenues.aggregate(total=models.Sum("total_amount"))["total"]
            or Decimal("0.00")
        )
        manual_cost_total = (
            self.manual_lines.filter(
                line_type=HiltonReportManualLine.LineType.COST
            ).aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        manual_adjustment_total = (
            self.manual_lines.filter(
                line_type=HiltonReportManualLine.LineType.ADJUSTMENT
            ).aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        self.gross_revenue = gross
        self.manual_cost_total = manual_cost_total
        self.manual_adjustment_total = manual_adjustment_total
        self.net_total = gross + manual_adjustment_total - manual_cost_total
        if save:
            self.save(
                update_fields=[
                    "gross_revenue",
                    "manual_cost_total",
                    "manual_adjustment_total",
                    "net_total",
                    "date_updated",
                ]
            )


class HiltonReportApartmentRevenue(models.Model):
    """Snapshot of one apartment's revenue inside a Hilton report interval."""

    report = models.ForeignKey(
        HiltonReport,
        on_delete=models.CASCADE,
        related_name="apartment_revenues",
        verbose_name=_("Rapport"),
    )
    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Appartement"),
    )
    apartment_nom = models.CharField(max_length=100, verbose_name=_("Appartement"))
    reservation_count = models.PositiveIntegerField(
        default=0, verbose_name=_("Nombre de réservations")
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant total"),
    )

    class Meta:
        verbose_name = _("Revenu appartement rapport Hilton")
        verbose_name_plural = _("Revenus appartements rapports Hilton")
        ordering = ("apartment_nom", "id")

    def __str__(self) -> str:
        return f"{self.apartment_nom} — {self.total_amount} MAD"


class HiltonReportManualLine(models.Model):
    """Manually entered cost, adjustment, or note for a Hilton report."""

    class LineType(models.TextChoices):
        COST = "cost", _("Coût")
        ADJUSTMENT = "adjustment", _("Ajustement")
        NOTE = "note", _("Note")

    report = models.ForeignKey(
        HiltonReport,
        on_delete=models.CASCADE,
        related_name="manual_lines",
        verbose_name=_("Rapport"),
    )
    line_type = models.CharField(
        max_length=20,
        choices=LineType.choices,
        default=LineType.COST,
        verbose_name=_("Type"),
    )
    description = models.CharField(max_length=300, verbose_name=_("Description"))
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant"),
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Ordre"))

    class Meta:
        verbose_name = _("Ligne manuelle rapport Hilton")
        verbose_name_plural = _("Lignes manuelles rapports Hilton")
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return f"{self.get_line_type_display()} — {self.description}"


class CostCategoryOption(models.Model):
    """Available cost categories for cost forms."""

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Catégorie de coût"),
    )

    class Meta:
        verbose_name = _("Catégorie de coût")
        verbose_name_plural = _("Catégories de coût")
        ordering = ("nom",)

    def __str__(self) -> str:
        return self.nom
