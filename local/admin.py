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
class LoyerAdmin(SimpleHistoryAdmin):
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


class HistoricalLocalAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical Local records."""

    list_display = (
        "history_id",
        "id",
        "nom",
        "type_local",
        "en_location",
        "locataire_nom",
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date", "type_local", "en_location")
    search_fields = ("nom", "locataire_nom")
    readonly_fields = [
        field.name
        for field in Local._meta.get_fields()
        if hasattr(field, "name") and not field.many_to_many and not field.one_to_many
    ] + [
        "history_id",
        "history_date",
        "history_change_reason",
        "history_type",
        "history_user",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class HistoricalLoyerAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical Loyer records."""

    list_display = (
        "history_id",
        "id",
        "local",
        "mois",
        "annee",
        "montant",
        "paye",
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date", "paye", "annee")
    search_fields = ("local__nom",)
    readonly_fields = [
        field.name
        for field in Loyer._meta.get_fields()
        if hasattr(field, "name") and not field.many_to_many and not field.one_to_many
    ] + [
        "history_id",
        "history_date",
        "history_change_reason",
        "history_type",
        "history_user",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(Local.history.model, HistoricalLocalAdmin)
admin.site.register(Loyer.history.model, HistoricalLoyerAdmin)
