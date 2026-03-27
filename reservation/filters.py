from datetime import timedelta

import django_filters
from django.db.models import F

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

    # Search box: maps to guest_name icontains
    search = django_filters.CharFilter(field_name="guest_name", lookup_expr="icontains")

    # Amount comparison filters
    amount = django_filters.NumberFilter(field_name="amount", lookup_expr="exact")
    amount__gt = django_filters.NumberFilter(field_name="amount", lookup_expr="gt")
    amount__gte = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount__lt = django_filters.NumberFilter(field_name="amount", lookup_expr="lt")
    amount__lte = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")
    amount__ne = django_filters.NumberFilter(method="filter_amount_ne")

    # Nights filters (computed field: check_out - check_in)
    nights = django_filters.NumberFilter(method="filter_nights_eq")
    nights__gt = django_filters.NumberFilter(method="filter_nights_gt")
    nights__gte = django_filters.NumberFilter(method="filter_nights_gte")
    nights__lt = django_filters.NumberFilter(method="filter_nights_lt")
    nights__lte = django_filters.NumberFilter(method="filter_nights_lte")

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

    def filter_amount_ne(self, qs, name, value):
        return qs.exclude(amount=value)

    def filter_nights_eq(self, qs, name, value):
        return qs.filter(check_out=F("check_in") + timedelta(days=int(value)))

    def filter_nights_gt(self, qs, name, value):
        return qs.filter(check_out__gt=F("check_in") + timedelta(days=int(value)))

    def filter_nights_gte(self, qs, name, value):
        return qs.filter(check_out__gte=F("check_in") + timedelta(days=int(value)))

    def filter_nights_lt(self, qs, name, value):
        return qs.filter(check_out__lt=F("check_in") + timedelta(days=int(value)))

    def filter_nights_lte(self, qs, name, value):
        return qs.filter(check_out__lte=F("check_in") + timedelta(days=int(value)))
