from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from local.models import Local, Loyer


class LocalListSerializer(serializers.ModelSerializer):
    rentabilite = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        read_only=True,
    )
    building_nom = serializers.CharField(
        source="building.nom", read_only=True, default=None
    )
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
        model = Local
        fields = [
            "id",
            "nom",
            "building",
            "building_nom",
            "type_local",
            "adresse",
            "superficie",
            "prix_achat",
            "prix_location_mensuel",
            "en_location",
            "locataire_nom",
            "date_debut_location",
            "notes",
            "rentabilite",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]
        read_only_fields = [
            "id",
            "rentabilite",
            "building_nom",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]


class LocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Local
        fields = [
            "id",
            "nom",
            "building",
            "type_local",
            "adresse",
            "superficie",
            "prix_achat",
            "prix_location_mensuel",
            "en_location",
            "locataire_nom",
            "date_debut_location",
            "notes",
            "created_by_user",
            "date_created",
            "date_updated",
        ]
        read_only_fields = [
            "id",
            "created_by_user",
            "date_created",
            "date_updated",
        ]


class LoyerListSerializer(serializers.ModelSerializer):
    local_nom = serializers.CharField(source="local.nom", read_only=True)
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
        model = Loyer
        fields = [
            "id",
            "local",
            "local_nom",
            "mois",
            "annee",
            "montant",
            "paye",
            "date_paiement",
            "notes",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]
        read_only_fields = [
            "id",
            "local_nom",
            "created_by_user",
            "created_by_user_name",
            "date_created",
            "date_updated",
        ]


class LoyerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loyer
        fields = [
            "id",
            "local",
            "mois",
            "annee",
            "montant",
            "paye",
            "date_paiement",
            "notes",
            "created_by_user",
            "date_created",
            "date_updated",
        ]
        read_only_fields = [
            "id",
            "created_by_user",
            "date_created",
            "date_updated",
        ]

    def validate_mois(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError(_("Le mois doit être entre 1 et 12."))
        return value

    def validate_annee(self, value):
        if value < 2000 or value > 2100:
            raise serializers.ValidationError(_("L'année doit être entre 2000 et 2100."))
        return value

    def validate(self, attrs):
        local = attrs.get("local") or (self.instance.local if self.instance else None)
        mois = attrs.get("mois") or (self.instance.mois if self.instance else None)
        annee = attrs.get("annee") or (self.instance.annee if self.instance else None)

        if local and mois and annee:
            qs = Loyer.objects.filter(local=local, mois=mois, annee=annee)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "mois": _(
                            "Un loyer existe déjà pour ce local "
                            "pour ce mois et cette année."
                        )
                    }
                )

        return attrs
