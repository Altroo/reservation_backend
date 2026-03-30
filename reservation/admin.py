from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Apartment, Cost, Notification, NotificationPreference, Reservation


class ApartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "nom")
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


class CostAdmin(admin.ModelAdmin):
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


class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "notify_check_in",
        "notify_check_out",
        "reminder_minutes",
    )
    list_filter = ("notify_check_in", "notify_check_out")
    readonly_fields = ("date_created", "date_updated")


class NotificationAdmin(admin.ModelAdmin):
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
