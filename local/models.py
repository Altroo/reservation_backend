from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from account.models import CustomUser


class LocalTypeOption(models.Model):
    """Available local types for local forms."""

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Type de local"),
    )

    class Meta:
        verbose_name = _("Type de local")
        verbose_name_plural = _("Types de local")
        ordering = ("nom",)

    def __str__(self):
        return self.nom


class Local(models.Model):
    TYPE_CHOICES = [
        ("Bureau", _("Bureau")),
        ("Magasin", _("Magasin")),
    ]

    nom = models.CharField(max_length=200, unique=True, verbose_name=_("Nom"))
    building = models.ForeignKey(
        "building.Building",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="locaux",
        verbose_name=_("Résidence"),
    )
    type_local = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name=_("Type de local"),
    )
    adresse = models.CharField(
        max_length=500, blank=True, default="", verbose_name=_("Adresse")
    )
    superficie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Superficie (m²)"),
    )
    prix_achat = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name=_("Prix d'achat")
    )
    prix_location_mensuel = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Prix de location mensuel HT"),
    )
    en_location = models.BooleanField(
        default=False, db_index=True, verbose_name=_("En location")
    )
    locataire_nom = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Nom du locataire")
    )
    date_debut_location = models.DateField(
        null=True, blank=True, verbose_name=_("Date de début de location")
    )
    notes = models.TextField(blank=True, default="", verbose_name=_("Notes"))
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locaux",
        verbose_name=_("Créé par"),
    )
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    date_updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Local")
        verbose_name_plural = _("Locaux")
        ordering = ("nom",)

    def __str__(self):
        return f"{self.nom} ({self.get_type_local_display()})"

    @property
    def rentabilite(self) -> Decimal:
        """Rentabilité (%) = [(prix_location_mensuel × 12) / prix_achat] × 100."""
        prix_achat = Decimal(str(self.prix_achat))
        prix_location = Decimal(str(self.prix_location_mensuel))
        if not prix_achat:
            return Decimal("0.00")
        return ((prix_location * 12) / prix_achat * 100).quantize(Decimal("0.01"))


class Loyer(models.Model):
    local = models.ForeignKey(
        Local,
        on_delete=models.PROTECT,
        related_name="loyers",
        verbose_name=_("Local"),
    )
    mois = models.IntegerField(db_index=True, verbose_name=_("Mois"))
    annee = models.IntegerField(db_index=True, verbose_name=_("Année"))
    montant = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_("Montant")
    )
    paye = models.BooleanField(default=False, db_index=True, verbose_name=_("Payé"))
    date_paiement = models.DateField(
        null=True, blank=True, verbose_name=_("Date de paiement")
    )
    notes = models.TextField(blank=True, default="", verbose_name=_("Notes"))
    created_by_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loyers",
        verbose_name=_("Créé par"),
    )
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    date_updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(
        verbose_name=_("Historique Loyer"),
        verbose_name_plural=_("Historiques Loyers"),
    )

    class Meta:
        verbose_name = _("Loyer")
        verbose_name_plural = _("Loyers")
        ordering = ("-annee", "-mois")
        constraints = [
            models.UniqueConstraint(
                fields=["local", "mois", "annee"],
                name="unique_loyer_per_local_month_year",
            ),
        ]
        indexes = [
            models.Index(fields=["local", "annee", "mois"]),
        ]

    def __str__(self):
        return f"{self.local.nom} — {self.mois:02d}/{self.annee} ({self.montant} MAD)"
