import django_filters
from django.db.models import Q

from local.models import Local, Loyer


class LocalFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="global_search", label="Search")
    type_local = django_filters.CharFilter(lookup_expr="iexact")
    en_location = django_filters.BooleanFilter()
    prix_achat__gte = django_filters.NumberFilter(
        field_name="prix_achat", lookup_expr="gte"
    )
    prix_achat__lte = django_filters.NumberFilter(
        field_name="prix_achat", lookup_expr="lte"
    )
    prix_location_mensuel__gte = django_filters.NumberFilter(
        field_name="prix_location_mensuel", lookup_expr="gte"
    )
    prix_location_mensuel__lte = django_filters.NumberFilter(
        field_name="prix_location_mensuel", lookup_expr="lte"
    )

    class Meta:
        model = Local
        fields = [
            "search",
            "type_local",
            "en_location",
            "prix_achat__gte",
            "prix_achat__lte",
            "prix_location_mensuel__gte",
            "prix_location_mensuel__lte",
        ]

    @staticmethod
    def global_search(queryset, _name, value):
        if not value or not value.strip():
            return queryset
        value = value.strip()
        return queryset.filter(
            Q(nom__icontains=value)
            | Q(locataire_nom__icontains=value)
            | Q(adresse__icontains=value)
        )


class LoyerFilter(django_filters.FilterSet):
    local = django_filters.NumberFilter(field_name="local_id")
    annee = django_filters.NumberFilter()
    mois = django_filters.NumberFilter()
    paye = django_filters.BooleanFilter()

    class Meta:
        model = Loyer
        fields = ["local", "annee", "mois", "paye"]
