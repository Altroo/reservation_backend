from rest_framework import serializers

from building.models import Building


class BuildingSerializer(serializers.ModelSerializer):
    created_by_user_name = serializers.SerializerMethodField()

    @staticmethod
    def get_created_by_user_name(obj):
        if obj.created_by_user:
            name = (
                f"{obj.created_by_user.first_name} " f"{obj.created_by_user.last_name}"
            ).strip()
            return name or obj.created_by_user.email
        return None

    class Meta:
        model = Building
        fields = [
            "id",
            "nom",
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
