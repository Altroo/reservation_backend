from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Apartment, Cost, Notification, NotificationPreference, Reservation


class ApartmentSerializer(serializers.ModelSerializer):
    building_nom = serializers.CharField(
        source="building.nom", read_only=True, default=None
    )

    class Meta:
        model = Apartment
        fields = ["id", "nom", "building", "building_nom"]
        read_only_fields = ["id", "building_nom"]


class ReservationListSerializer(serializers.ModelSerializer):
    apartment_nom = serializers.CharField(source="apartment.nom", read_only=True)
    apartment_building = serializers.IntegerField(
        source="apartment.building_id", read_only=True, default=None
    )
    apartment_building_nom = serializers.CharField(
        source="apartment.building.nom", read_only=True, default=None
    )
    payment_source_display = serializers.CharField(
        source="get_payment_source_display", read_only=True
    )
    created_by_user_name = serializers.SerializerMethodField()
    nights = serializers.SerializerMethodField()

    @staticmethod
    def get_nights(obj):
        return obj.nights

    @staticmethod
    def get_created_by_user_name(obj):
        if obj.created_by_user:
            name = f"{obj.created_by_user.first_name} {obj.created_by_user.last_name}".strip()
            return name or obj.created_by_user.email
        return None

    class Meta:
        model = Reservation
        fields = [
            "id",
            "apartment",
            "apartment_nom",
            "apartment_building",
            "apartment_building_nom",
            "guest_name",
            "check_in",
            "check_out",
            "nights",
            "amount",
            "payment_source",
            "payment_source_display",
            "amount_returned",
            "notes",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]
        read_only_fields = [
            "id",
            "apartment_nom",
            "apartment_building",
            "apartment_building_nom",
            "payment_source_display",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]


class ReservationSerializer(serializers.ModelSerializer):
    """Full create / update serializer."""

    class Meta:
        model = Reservation
        fields = [
            "id",
            "apartment",
            "guest_name",
            "check_in",
            "check_out",
            "amount",
            "payment_source",
            "amount_returned",
            "notes",
            "created_by_user",
            "date_created",
            "date_updated",
        ]
        read_only_fields = ["id", "created_by_user", "date_created", "date_updated"]

    def validate(self, attrs):
        check_in = attrs.get("check_in") or (
            self.instance.check_in if self.instance else None
        )
        check_out = attrs.get("check_out") or (
            self.instance.check_out if self.instance else None
        )
        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError(
                {
                    "check_out": _("La date de départ doit être postérieure à la date d'arrivée.")
                }
            )

        apartment = attrs.get("apartment") or (
            self.instance.apartment if self.instance else None
        )
        if apartment and check_in and check_out:
            overlapping = Reservation.objects.filter(
                apartment=apartment,
                check_in__lt=check_out,
                check_out__gt=check_in,
            )
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            overlap = overlapping.first()
            if overlap:
                raise serializers.ValidationError(
                    {
                        "check_in": (
                            _("Cette réservation chevauche une réservation existante")
                            + f" ({overlap.guest_name}: {overlap.check_in} — {overlap.check_out})."
                        )
                    }
                )

        return attrs


class CostSerializer(serializers.ModelSerializer):
    """Serializer for cost entries."""

    created_by_user_name = serializers.SerializerMethodField()

    @staticmethod
    def get_created_by_user_name(obj):
        if obj.created_by_user:
            name = f"{obj.created_by_user.first_name} {obj.created_by_user.last_name}".strip()
            return name or obj.created_by_user.email
        return None

    class Meta:
        model = Cost
        fields = [
            "id",
            "description",
            "amount",
            "date",
            "category",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]
        read_only_fields = [
            "id",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]


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
