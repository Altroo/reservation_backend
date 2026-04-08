from rest_framework import serializers

from notification.models import Notification, NotificationPreference


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "notify_check_in",
            "notify_check_out",
            "reminder_minutes",
            "date_created",
            "date_updated",
        ]
        read_only_fields = ["id", "date_created", "date_updated"]


class NotificationSerializer(serializers.ModelSerializer):
    reservation_id = serializers.IntegerField(
        source="reservation.id", read_only=True, default=None
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "reservation_id",
            "title",
            "message",
            "notification_type",
            "is_read",
            "date_created",
        ]
        read_only_fields = [
            "id",
            "reservation_id",
            "title",
            "message",
            "notification_type",
            "date_created",
        ]
