from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

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


class PaymentSourceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSourceOption
        fields = ["id", "nom"]
        read_only_fields = ["id"]


class CostCategoryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCategoryOption
        fields = ["id", "nom"]
        read_only_fields = ["id"]


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
                    "check_out": _(
                        "La date de départ doit être postérieure à la date d'arrivée."
                    )
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
    building_nom = serializers.CharField(
        source="building.nom", read_only=True, default=None
    )

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
            "building",
            "building_nom",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]
        read_only_fields = [
            "id",
            "created_by_user",
            "created_by_user_name",
            "building_nom",
            "date_created",
            "date_updated",
        ]


class HiltonReportApartmentRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiltonReportApartmentRevenue
        fields = [
            "id",
            "apartment",
            "apartment_nom",
            "reservation_count",
            "total_amount",
        ]
        read_only_fields = fields


class HiltonReportManualLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiltonReportManualLine
        fields = [
            "id",
            "line_type",
            "description",
            "amount",
            "operations_count",
            "sort_order",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        line_type = attrs.get("line_type") or HiltonReportManualLine.LineType.COST
        amount = attrs.get("amount", 0)
        if amount < 0:
            raise serializers.ValidationError(
                {"amount": _("Le montant doit être positif.")}
            )
        if line_type == HiltonReportManualLine.LineType.NOTE:
            attrs["amount"] = 0
            attrs["operations_count"] = None
        return attrs


class HiltonReportSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiltonReportSettings
        fields = ["id", "carry_forward_balance", "date_updated"]
        read_only_fields = ["id", "date_updated"]


class HiltonReportSerializer(serializers.ModelSerializer):
    apartment_revenues = HiltonReportApartmentRevenueSerializer(many=True, read_only=True)
    manual_lines = HiltonReportManualLineSerializer(many=True, read_only=True)
    building_name = serializers.SerializerMethodField()
    created_by_user_name = serializers.SerializerMethodField()

    @staticmethod
    def get_building_name(_):
        return "Hilton residence"

    @staticmethod
    def get_created_by_user_name(obj):
        if obj.created_by_user:
            name = f"{obj.created_by_user.first_name} {obj.created_by_user.last_name}".strip()
            return name or obj.created_by_user.email
        return None

    class Meta:
        model = HiltonReport
        fields = [
            "id",
            "building_name",
            "start_date",
            "end_date",
            "notes",
            "opening_balance",
            "cash_register_total",
            "cost_period_label",
            "gross_revenue",
            "manual_cost_total",
            "manual_adjustment_total",
            "booking_total",
            "airbnb_total",
            "cash_revenue_total",
            "cash_total",
            "bank_total",
            "net_total",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
            "apartment_revenues",
            "manual_lines",
        ]
        read_only_fields = fields


class HiltonReportMutationSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    cash_register_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    cost_period_label = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    manual_lines = HiltonReportManualLineSerializer(many=True, required=False)
