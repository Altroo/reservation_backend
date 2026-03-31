from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from account.models import CustomUser


class Apartment(models.Model):
    """Représente un appartement / unité louée."""

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom de l'appartement",
        help_text="Nom de l'appartement",
    )
    building = models.ForeignKey(
        "building.Building",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="apartments",
        verbose_name=_("Résidence"),
    )

    class Meta:
        verbose_name = "Appartement"
        verbose_name_plural = "Appartements"
        ordering = ("nom",)

    def __str__(self) -> str:
        return self.nom


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


class Cost(models.Model):
    """Represents a cost entry (maintenance, charges, taxes, etc.)."""

    CATEGORY_CHOICES = [
        ("Entretien", "Entretien"),
        ("Charges", "Charges"),
        ("Assurance", "Assurance"),
        ("Taxes", "Taxes"),
        ("Autre", "Autre"),
    ]

    description = models.CharField(
        max_length=300,
        verbose_name="Description",
        help_text="Description du coût",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant (MAD)",
    )
    date = models.DateField(verbose_name="Date", db_index=True)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="Autre",
        verbose_name="Catégorie",
        db_index=True,
    )
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="costs_created",
        verbose_name="Créé par",
    )
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date création")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date modification")

    class Meta:
        verbose_name = "Coût"
        verbose_name_plural = "Coûts"
        ordering = ("-date",)

    def __str__(self) -> str:
        return f"{self.description} — {self.amount} MAD ({self.date})"


class NotificationPreference(models.Model):
    """User-specific notification preferences for reservation reminders."""

    REMINDER_CHOICES = [
        (0, "Au moment de l'événement"),
        (15, "15 minutes avant"),
        (30, "30 minutes avant"),
        (60, "1 heure avant"),
        (120, "2 heures avant"),
        (1440, "1 jour avant"),
        (2880, "2 jours avant"),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notification_preference",
        verbose_name="Utilisateur",
    )
    notify_check_in = models.BooleanField(
        default=True,
        verbose_name="Notifier à l'arrivée",
    )
    notify_check_out = models.BooleanField(
        default=True,
        verbose_name="Notifier au départ",
    )
    reminder_minutes = models.IntegerField(
        choices=REMINDER_CHOICES,
        default=60,
        verbose_name="Rappel avant (minutes)",
    )
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date création")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date modification")

    class Meta:
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notification"

    def __str__(self) -> str:
        return f"Notifications — {self.user.email}"


class Notification(models.Model):
    """A notification sent to a user about a reservation event."""

    NOTIFICATION_TYPES = [
        ("check_in", "Arrivée"),
        ("check_out", "Départ"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Utilisateur",
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="Réservation",
    )
    title = models.CharField(max_length=255, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name="Type",
    )
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name="Date création", db_index=True
    )

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ("-date_created",)

    def __str__(self) -> str:
        return f"{self.title} — {self.user.email}"
