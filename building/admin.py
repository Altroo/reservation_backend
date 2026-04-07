from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from building.models import Building


@admin.register(Building)
class BuildingAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nom", "date_created")
    search_fields = ("nom",)
    ordering = ("nom",)
    readonly_fields = ("date_created", "date_updated")


class HistoricalBuildingAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical Building records."""

    list_display = (
        "history_id",
        "id",
        "nom",
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date")
    search_fields = ("nom",)
    readonly_fields = [
        field.name
        for field in Building._meta.get_fields()
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


admin.site.register(Building.history.model, HistoricalBuildingAdmin)
