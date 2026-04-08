from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from account.models import CustomUser


class NotificationPreference(models.Model):
    """User-specific notification preferences for reservation reminders."""

    REMINDER_CHOICES = [
        (0, _("Au moment de l'événement")),
        (15, _("15 minutes avant")),
        (30, _("30 minutes avant")),
        (60, _("1 heure avant")),
        (120, _("2 heures avant")),
        (1440, _("1 jour avant")),
        (2880, _("2 jours avant")),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notification_preference",
        verbose_name=_("Utilisateur"),
    )
    notify_check_in = models.BooleanField(
        default=True,
        verbose_name=_("Notifier à l'arrivée"),
    )
    notify_check_out = models.BooleanField(
        default=True,
        verbose_name=_("Notifier au départ"),
    )
    reminder_minutes = models.IntegerField(
        choices=REMINDER_CHOICES,
        default=60,
        verbose_name=_("Rappel avant (minutes)"),
    )
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date création")
    )
    date_updated = models.DateTimeField(
        auto_now=True, verbose_name=_("Date modification")
    )
    history = HistoricalRecords(
        verbose_name=_("Historique Préférence Notification"),
        verbose_name_plural=_("Historiques Préférences Notifications"),
    )

    class Meta:
        verbose_name = _("Préférence de notification")
        verbose_name_plural = _("Préférences de notification")
        db_table = "reservation_notificationpreference"

    def __str__(self) -> str:
        return f"Notifications — {self.user.email}"


class Notification(models.Model):
    """A notification sent to a user about a reservation event."""

    NOTIFICATION_TYPES = [
        ("check_in", _("Arrivée")),
        ("check_out", _("Départ")),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Utilisateur"),
    )
    reservation = models.ForeignKey(
        "reservation.Reservation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("Réservation"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Titre"))
    message = models.TextField(verbose_name=_("Message"))
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name=_("Type"),
    )
    is_read = models.BooleanField(default=False, verbose_name=_("Lu"))
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date création"), db_index=True
    )
    history = HistoricalRecords(
        verbose_name=_("Historique Notification"),
        verbose_name_plural=_("Historiques Notifications"),
    )

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ("-date_created",)
        db_table = "reservation_notification"

    def __str__(self) -> str:
        return f"{self.title} — {self.user.email}"
