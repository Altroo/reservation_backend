from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Apartment, Cost, Notification, NotificationPreference, Reservation


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
        "created_by_user",
        "date_created",
    )
    list_filter = ("category", "date")
    search_fields = ("description",)
    date_hierarchy = "date"
    ordering = ("-date",)
    readonly_fields = ("date_created", "date_updated")


admin.site.register(Apartment, ApartmentAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Cost, CostAdmin)


class NotificationPreferenceAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "user",
        "notify_check_in",
        "notify_check_out",
        "reminder_minutes",
    )
    list_filter = ("notify_check_in", "notify_check_out")
    readonly_fields = ("date_created", "date_updated")


class NotificationAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "notification_type",
        "is_read",
        "date_created",
    )
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "message")
    ordering = ("-date_created",)
    readonly_fields = ("date_created",)


admin.site.register(NotificationPreference, NotificationPreferenceAdmin)
admin.site.register(Notification, NotificationAdmin)


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
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date", "category")
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


class HistoricalNotificationPreferenceAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical NotificationPreference records."""

    list_display = (
        "history_id",
        "id",
        "user",
        "notify_check_in",
        "notify_check_out",
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date")
    readonly_fields = [
        field.name
        for field in NotificationPreference._meta.get_fields()
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


class HistoricalNotificationAdmin(admin.ModelAdmin):
    """Read-only admin for viewing historical Notification records."""

    list_display = (
        "history_id",
        "id",
        "user",
        "title",
        "notification_type",
        "is_read",
        "history_type",
        "history_date",
        "history_user",
    )
    list_filter = ("history_type", "history_date", "notification_type", "is_read")
    search_fields = ("title", "message")
    readonly_fields = [
        field.name
        for field in Notification._meta.get_fields()
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
admin.site.register(NotificationPreference.history.model, HistoricalNotificationPreferenceAdmin)
admin.site.register(Notification.history.model, HistoricalNotificationAdmin)
