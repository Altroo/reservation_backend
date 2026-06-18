from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Apartment,
    Cost,
    CostCategoryOption,
    HiltonReport,
    HiltonReportApartmentRevenue,
    HiltonReportManualLine,
    HiltonReportSettings,
    PaymentSourceOption,
    Reservation,
)


HISTORY_FIELDS = (
    "history_id",
    "history_date",
    "history_change_reason",
    "history_type",
    "history_user",
)


def _history_readonly_fields(model):
    return [
        field.name
        for field in model._meta.get_fields()
        if hasattr(field, "name")
        and getattr(field, "concrete", False)
        and not field.many_to_many
    ] + list(HISTORY_FIELDS)


def _history_admin_class(model, display_fields, list_filter=(), search_fields=()):
    attrs = {
        "__doc__": f"Read-only admin for viewing historical {model.__name__} records.",
        "list_display": (
            "history_id",
            *display_fields,
            "history_type",
            "history_date",
            "history_user",
        ),
        "list_filter": ("history_type", "history_date", *list_filter),
        "search_fields": search_fields,
        "readonly_fields": _history_readonly_fields(model),
        "ordering": ("-history_date", "-history_id"),
        "has_add_permission": lambda self, request: False,
        "has_delete_permission": lambda self, request, obj=None: False,
        "has_change_permission": lambda self, request, obj=None: False,
    }
    return type(f"Historical{model.__name__}Admin", (admin.ModelAdmin,), attrs)


def register_history_admin(model, *, display_fields=("id",), list_filter=(), search_fields=()):
    admin_class = _history_admin_class(model, display_fields, list_filter, search_fields)
    try:
        admin.site.register(model.history.model, admin_class)
    except AlreadyRegistered:
        pass


class PaymentSourceOptionAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nom")
    search_fields = ("nom",)
    ordering = ("nom",)


class CostCategoryOptionAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nom")
    search_fields = ("nom",)
    ordering = ("nom",)


class ApartmentAdmin(SimpleHistoryAdmin):
    list_display = ("id", "nom", "building")
    list_filter = ("building",)
    search_fields = ("nom",)
    ordering = ("nom",)


class ReservationAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "guest_name",
        "apartment",
        "check_in",
        "check_out",
        "amount",
        "payment_source",
        "created_by_user",
        "date_created",
    )
    list_filter = ("payment_source", "apartment", "check_in")
    search_fields = ("guest_name",)
    date_hierarchy = "check_in"
    ordering = ("-check_in",)
    readonly_fields = ("date_created", "date_updated")


class CostAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "description",
        "amount",
        "date",
        "category",
        "building",
        "created_by_user",
        "date_created",
    )
    list_filter = ("category", "building", "date")
    search_fields = ("description",)
    date_hierarchy = "date"
    ordering = ("-date",)
    readonly_fields = ("date_created", "date_updated")


class HiltonReportApartmentRevenueInline(admin.TabularInline):
    model = HiltonReportApartmentRevenue
    extra = 0
    readonly_fields = (
        "apartment",
        "apartment_nom",
        "reservation_count",
        "total_amount",
    )
    can_delete = False


class HiltonReportManualLineInline(admin.TabularInline):
    model = HiltonReportManualLine
    extra = 0


class HiltonReportAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "start_date",
        "end_date",
        "opening_balance",
        "gross_revenue",
        "manual_cost_total",
        "manual_adjustment_total",
        "booking_total",
        "airbnb_total",
        "cash_total",
        "bank_total",
        "net_total",
        "created_by_user",
        "date_created",
    )
    list_filter = ("start_date", "end_date", "created_by_user")
    search_fields = ("notes",)
    date_hierarchy = "end_date"
    ordering = ("-end_date", "-id")
    readonly_fields = (
        "gross_revenue",
        "opening_balance",
        "manual_cost_total",
        "manual_adjustment_total",
        "booking_total",
        "airbnb_total",
        "cash_revenue_total",
        "cash_total",
        "bank_total",
        "net_total",
        "date_created",
        "date_updated",
    )
    inlines = (HiltonReportApartmentRevenueInline, HiltonReportManualLineInline)


class HiltonReportSettingsAdmin(SimpleHistoryAdmin):
    list_display = ("carry_forward_balance", "date_updated")
    readonly_fields = ("date_updated",)

    def has_add_permission(self, request):
        return not HiltonReportSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class HiltonReportApartmentRevenueAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "report",
        "apartment",
        "apartment_nom",
        "reservation_count",
        "total_amount",
    )
    list_filter = ("report", "apartment")
    search_fields = ("apartment_nom", "report__notes")
    ordering = ("report", "apartment_nom", "id")


class HiltonReportManualLineAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "report",
        "line_type",
        "description",
        "amount",
        "operations_count",
        "sort_order",
    )
    list_filter = ("line_type", "report")
    search_fields = ("description", "report__notes")
    ordering = ("report", "sort_order", "id")


admin.site.register(PaymentSourceOption, PaymentSourceOptionAdmin)
admin.site.register(Apartment, ApartmentAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Cost, CostAdmin)
admin.site.register(HiltonReport, HiltonReportAdmin)
admin.site.register(HiltonReportSettings, HiltonReportSettingsAdmin)
admin.site.register(HiltonReportApartmentRevenue, HiltonReportApartmentRevenueAdmin)
admin.site.register(HiltonReportManualLine, HiltonReportManualLineAdmin)
admin.site.register(CostCategoryOption, CostCategoryOptionAdmin)


# Historical Model Admins (Read-only)
class HistoricalApartmentAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical Apartment records."""

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
        for field in Apartment._meta.get_fields()
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


class HistoricalReservationAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical Reservation records."""

    list_display = (
        "history_id",
        "id",
        "guest_name",
        "apartment",
        "check_in",
        "check_out",
        "amount",
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date", "payment_source")
    search_fields = ("guest_name",)
    readonly_fields = [
        field.name
        for field in Reservation._meta.get_fields()
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


class HistoricalCostAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical Cost records."""

    list_display = (
        "history_id",
        "id",
        "description",
        "amount",
        "date",
        "category",
        "building",
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date", "category", "building")
    search_fields = ("description",)
    readonly_fields = [
        field.name
        for field in Cost._meta.get_fields()
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


admin.site.register(Apartment.history.model, HistoricalApartmentAdmin)
admin.site.register(Reservation.history.model, HistoricalReservationAdmin)
admin.site.register(Cost.history.model, HistoricalCostAdmin)
register_history_admin(
    PaymentSourceOption,
    display_fields=("id", "nom"),
    search_fields=("nom",),
)
register_history_admin(
    HiltonReportSettings,
    display_fields=("id", "singleton_key", "carry_forward_balance", "date_updated"),
)
register_history_admin(
    HiltonReport,
    display_fields=("id", "start_date", "end_date", "cash_total", "bank_total", "net_total", "created_by_user", "date_created"),
    list_filter=("start_date", "end_date", "created_by_user"),
    search_fields=("notes",),
)
register_history_admin(
    HiltonReportApartmentRevenue,
    display_fields=("id", "report", "apartment", "apartment_nom", "reservation_count", "total_amount"),
    list_filter=("report", "apartment"),
    search_fields=("apartment_nom", "report__notes"),
)
register_history_admin(
    HiltonReportManualLine,
    display_fields=("id", "report", "line_type", "description", "amount", "operations_count", "sort_order"),
    list_filter=("line_type", "report"),
    search_fields=("description", "report__notes"),
)
register_history_admin(
    CostCategoryOption,
    display_fields=("id", "nom"),
    search_fields=("nom",),
)
