from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from building.models import Building


@admin.register(Building)
class BuildingAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nom", "date_created")
    search_fields = ("nom",)
    ordering = ("nom",)
    readonly_fields = ("date_created", "date_updated")
