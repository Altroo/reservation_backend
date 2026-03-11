import django_filters

from .models import Reservation


class ReservationFilter(django_filters.FilterSet):
    guest_name = django_filters.CharFilter(lookup_expr="icontains")
    payment_source = django_filters.CharFilter(lookup_expr="iexact")
    apartment = django_filters.NumberFilter()
    check_in_after = django_filters.DateFilter(field_name="check_in", lookup_expr="gte")
    check_in_before = django_filters.DateFilter(
        field_name="check_in", lookup_expr="lte"
    )
    check_out_after = django_filters.DateFilter(
        field_name="check_out", lookup_expr="gte"
    )
    check_out_before = django_filters.DateFilter(
        field_name="check_out", lookup_expr="lte"
    )
    year = django_filters.NumberFilter(field_name="check_in", lookup_expr="year")
    month = django_filters.NumberFilter(field_name="check_in", lookup_expr="month")

    class Meta:
        model = Reservation
        fields = [
            "guest_name",
            "payment_source",
            "apartment",
            "check_in_after",
            "check_in_before",
            "check_out_after",
            "check_out_before",
            "year",
            "month",
        ]
