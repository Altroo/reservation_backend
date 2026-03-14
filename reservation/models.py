from django.db import models
from simple_history.models import HistoricalRecords

from account.models import CustomUser


class Apartment(models.Model):
    """Représente un appartement / unité louée."""

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Code",
        help_text="Identifiant court de l'appartement (ex: 5B)",
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Nom",
        help_text="Nom complet de l'appartement",
    )
    monthly_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Coût mensuel",
        help_text="Coût mensuel de location de l'appartement (MAD)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif",
        db_index=True,
    )

    class Meta:
        verbose_name = "Appartement"
        verbose_name_plural = "Appartements"
        ordering = ("code",)

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Reservation(models.Model):
    """Représente une réservation pour un appartement sur une date donnée."""

    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.PROTECT,
        related_name="reservations",
        verbose_name="Appartement",
    )
    guest_name = models.CharField(
        max_length=200,
        verbose_name="Nom du client",
        help_text="Nom complet du client",
    )
    check_in = models.DateField(
        verbose_name="Date d'arrivée",
        db_index=True,
    )
    check_out = models.DateField(
        verbose_name="Date de départ",
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant (MAD)",
        help_text="Montant total de la réservation en MAD",
    )
    payment_source = models.CharField(
        max_length=50,
        default="Cash",
        verbose_name="Source de paiement",
        db_index=True,
    )
    amount_returned = models.BooleanField(
        default=False,
        verbose_name="Montant retourné",
        help_text="Indique si le montant a été retourné",
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes",
    )
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations_created",
        verbose_name="Créé par",
    )
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name="Date création", db_index=True
    )
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date modification")

    history = HistoricalRecords(
        verbose_name="Historique Réservation",
        verbose_name_plural="Historiques Réservations",
    )

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
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
