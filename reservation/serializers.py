from rest_framework import serializers

from .models import Apartment, Reservation


class ApartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = ["id", "code", "name", "monthly_cost", "is_active"]
        read_only_fields = ["id"]


class ReservationListSerializer(serializers.ModelSerializer):
    apartment_name = serializers.CharField(source="apartment.name", read_only=True)
    apartment_code = serializers.CharField(source="apartment.code", read_only=True)
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
            "apartment_name",
            "apartment_code",
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
            "apartment_name",
            "apartment_code",
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
                    "check_out": "La date de départ doit être postérieure à la date d'arrivée."
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
                            f"Cette réservation chevauche une réservation existante "
                            f"({overlap.guest_name}: {overlap.check_in} — {overlap.check_out})."
                        )
                    }
                )

        return attrs
