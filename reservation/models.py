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
