from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from account.models import CustomUser


class Building(models.Model):
    """Représente une résidence / immeuble regroupant des appartements et locaux."""

    nom = models.CharField(
        max_length=200,
        unique=True,
        verbose_name=_("Nom"),
        help_text=_("Nom de la résidence"),
    )
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="buildings",
        verbose_name=_("Créé par"),
    )
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    date_updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Résidence")
        verbose_name_plural = _("Résidences")
        ordering = ("nom",)

    def __str__(self) -> str:
        return self.nom
