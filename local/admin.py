from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from local.models import Local, Loyer


@admin.register(Local)
class LocalAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "nom",
        "building",
        "type_local",
        "en_location",
        "locataire_nom",
        "prix_location_mensuel",
        "prix_achat",
        "date_created",
    )
    list_filter = ("building", "type_local", "en_location")
    search_fields = ("nom", "locataire_nom", "adresse")
    ordering = ("nom",)
    readonly_fields = ("date_created", "date_updated")


@admin.register(Loyer)
class LoyerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "local",
        "mois",
        "annee",
        "montant",
        "paye",
        "date_paiement",
        "date_created",
    )
    list_filter = ("paye", "annee", "mois", "local")
    search_fields = ("local__nom",)
    ordering = ("-annee", "-mois")
    readonly_fields = ("date_created", "date_updated")
