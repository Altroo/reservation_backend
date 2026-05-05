from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Apartment,
    Cost,
    HiltonReport,
    HiltonReportApartmentRevenue,
    HiltonReportManualLine,
    Reservation,
)


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


class HiltonReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "start_date",
        "end_date",
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


admin.site.register(Apartment, ApartmentAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Cost, CostAdmin)
admin.site.register(HiltonReport, HiltonReportAdmin)


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
