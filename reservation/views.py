from datetime import date

from django.db.models import Sum, Count
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import CustomPagination
from core.permissions import can_create, can_update, can_delete
from .filters import ReservationFilter
from .models import Apartment, Reservation
from .serializers import (
    ApartmentSerializer,
    ReservationListSerializer,
    ReservationSerializer,
)


class ApartmentListView(APIView):
    """GET all active apartments, POST create a new apartment."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        apartments = Apartment.objects.filter(is_active=True)
        serializer = ApartmentSerializer(apartments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        nom = request.data.get("nom", "").strip()
        if not nom:
            raise ValidationError({"nom": [_("Ce champ est requis.")]})
        code = nom[:20]
        if Apartment.objects.filter(code=code).exists():
            raise ValidationError({"nom": [_("Un appartement avec ce code existe déjà.")]})
        apartment = Apartment.objects.create(code=code, name=nom, is_active=True)
        serializer = ApartmentSerializer(apartment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReservationListCreateView(APIView):
    """GET paginated/full reservation list and POST create a new reservation."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        pagination = request.query_params.get("pagination", "false").lower() == "true"
        base_qs = (
            Reservation.objects.all()
            .select_related("apartment", "created_by_user")
            .order_by("-check_in", "-id")
        )
        filterset = ReservationFilter(request.GET, queryset=base_qs)
        qs = filterset.qs

        if pagination:
            paginator = CustomPagination()
            page = paginator.paginate_queryset(qs, request)
            serializer = ReservationListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ReservationListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        if not can_create(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour créer une réservation.")
            )
        serializer = ReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by_user=request.user)
        return Response(
            ReservationListSerializer(instance).data, status=status.HTTP_201_CREATED
        )


class ReservationDetailEditDeleteView(APIView):
    """GET, PUT, DELETE a single reservation."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_reservation(pk: int) -> Reservation:
        try:
            return Reservation.objects.select_related(
                "apartment", "created_by_user"
            ).get(pk=pk)
        except Reservation.DoesNotExist:
            raise Http404(_("Aucune réservation ne correspond à la requête."))

    def get(self, request, pk: int):
        reservation = self._get_reservation(pk)
        serializer = ReservationListSerializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier cette réservation.")
            )
        reservation = self._get_reservation(pk)
        serializer = ReservationSerializer(reservation, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by_user=reservation.created_by_user)
        return Response(
            ReservationListSerializer(self._get_reservation(pk)).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer cette réservation.")
            )
        reservation = self._get_reservation(pk)
        reservation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulkDeleteReservationView(APIView):
    """DELETE multiple reservations by id list."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def delete(request):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer des réservations.")
            )
        ids = request.data.get("ids", [])
        if not ids or not isinstance(ids, list):
            raise ValidationError({"ids": _("Une liste d'identifiants est requise.")})
        Reservation.objects.filter(pk__in=ids).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardStatsView(APIView):
    """Global KPI stats: revenue, occupancy, source breakdown."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        year = request.query_params.get("year", date.today().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            raise ValidationError({"year": _("year doit être un entier valide.")})

        qs = Reservation.objects.filter(check_in__year=year)

        total_revenue = qs.aggregate(total=Sum("amount"))["total"] or 0

        # Revenue by source
        by_source = (
            qs.values("payment_source")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("payment_source")
        )

        # Monthly revenue
        monthly = (
            qs.values("check_in__month")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("check_in__month")
        )
        monthly_data = {i: {"total": 0, "count": 0} for i in range(1, 13)}
        for m in monthly:
            monthly_data[m["check_in__month"]] = {
                "total": float(m["total"] or 0),
                "count": m["count"],
            }

        # Revenue per apartment
        by_apartment = (
            qs.values("apartment__code", "apartment__name")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("apartment__code")
        )

        # Occupancy: occupied days per apartment per month
        apartments = list(
            Apartment.objects.filter(is_active=True).values("id", "code", "name")
        )
        occupancy_by_apt = {}
        for apt in apartments:
            apt_qs = qs.filter(apartment_id=apt["id"])
            occupied_days = sum(r.nights for r in apt_qs) if apt_qs.exists() else 0
            occupancy_by_apt[apt["code"]] = {
                "name": apt["name"],
                "occupied_days": occupied_days,
                "reservation_count": apt_qs.count(),
                "revenue": float(apt_qs.aggregate(t=Sum("amount"))["t"] or 0),
            }

        # Daily revenue (grouped by check_in date)
        daily = (
            qs.values("check_in")
            .annotate(total=Sum("amount"))
            .order_by("check_in")
        )
        daily_revenue = [
            {"date": str(d["check_in"]), "total": float(d["total"] or 0)}
            for d in daily
        ]

        return Response(
            {
                "year": year,
                "total_revenue": float(total_revenue),
                "by_source": [
                    {
                        "source": item["payment_source"],
                        "total": float(item["total"] or 0),
                        "count": item["count"],
                    }
                    for item in by_source
                ],
                "monthly_revenue": [
                    {"month": m, **monthly_data[m]} for m in range(1, 13)
                ],
                "by_apartment": [
                    {
                        "code": item["apartment__code"],
                        "name": item["apartment__name"],
                        "total": float(item["total"] or 0),
                        "count": item["count"],
                    }
                    for item in by_apartment
                ],
                "occupancy_by_apartment": occupancy_by_apt,
                "daily_revenue": daily_revenue,
            },
            status=status.HTTP_200_OK,
        )


class PlanningMonthView(APIView):
    """Returns all reservations for a given year/month, grouped by apartment."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        year = request.query_params.get("year", date.today().year)
        month = request.query_params.get("month", date.today().month)
        try:
            year, month = int(year), int(month)
        except (ValueError, TypeError):
            raise ValidationError(
                {"error": _("year et month doivent être des entiers valides.")}
            )

        # Include reservations that overlap with the requested month
        from datetime import date as dt
        import calendar

        last_day = calendar.monthrange(year, month)[1]
        month_start = dt(year, month, 1)
        month_end = dt(year, month, last_day)

        qs = (
            Reservation.objects.filter(
                check_in__lte=month_end,
                check_out__gt=month_start,
            )
            .select_related("apartment")
            .order_by("apartment__code", "check_in")
        )

        apartments = list(Apartment.objects.filter(is_active=True).order_by("code"))

        result = {}
        for apt in apartments:
            apt_reservations = [r for r in qs if r.apartment_id == apt.id]
            result[apt.code] = {
                "id": apt.id,
                "name": apt.name,
                "reservations": ReservationListSerializer(
                    apt_reservations, many=True
                ).data,
            }

        return Response(
            {
                "year": year,
                "month": month,
                "last_day": last_day,
                "apartments": result,
            },
            status=status.HTTP_200_OK,
        )


class BalanceView(APIView):
    """Balance page: revenue from Airbnb & Bank sources with returned/not-returned breakdown."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        year = request.query_params.get("year", date.today().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            raise ValidationError({"year": _("year doit être un entier valide.")})

        # Only Airbnb & Bank (virement) sources
        balance_sources = ["Airbnb", "Bank"]
        qs = Reservation.objects.filter(
            check_in__year=year,
            payment_source__in=balance_sources,
        ).select_related("apartment")

        apartments = list(Apartment.objects.filter(is_active=True).order_by("code"))

        # Build monthly matrix per apartment
        matrix = {}
        for apt in apartments:
            monthly = {m: {"total": 0.0, "count": 0} for m in range(1, 13)}
            apt_qs = qs.filter(apartment_id=apt.id)
            for r in apt_qs:
                m = r.check_in.month
                monthly[m]["total"] += float(r.amount)
                monthly[m]["count"] += 1
            year_total = sum(v["total"] for v in monthly.values())
            matrix[apt.code] = {
                "name": apt.name,
                "monthly": monthly,
                "year_total": year_total,
            }

        # Returned vs not-returned breakdown
        total_returned = sum(float(r.amount) for r in qs if r.amount_returned)
        total_not_returned = sum(float(r.amount) for r in qs if not r.amount_returned)

        total_monthly_cost = sum(
            float(apt.monthly_cost) for apt in apartments
        )

        # Individual reservations for the detail table
        reservations = [
            {
                "id": r.id,
                "apartment_code": r.apartment.code,
                "apartment_name": r.apartment.name,
                "guest_name": r.guest_name,
                "check_in": str(r.check_in),
                "check_out": str(r.check_out),
                "amount": float(r.amount),
                "payment_source": r.payment_source,
                "amount_returned": r.amount_returned,
            }
            for r in qs.order_by("apartment__code", "check_in")
        ]

        return Response(
            {
                "year": year,
                "apartments": matrix,
                "total_returned": total_returned,
                "total_not_returned": total_not_returned,
                "total_monthly_cost": total_monthly_cost,
                "reservations": reservations,
            },
            status=status.HTTP_200_OK,
        )


class ToggleAmountReturnedView(APIView):
    """Toggle the amount_returned flag on a reservation."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def patch(request, pk: int):
        try:
            reservation = Reservation.objects.get(pk=pk)
        except Reservation.DoesNotExist:
            raise Http404(_("Aucune réservation ne correspond à la requête."))

        amount_returned = request.data.get("amount_returned")
        if amount_returned is None or not isinstance(amount_returned, bool):
            raise ValidationError(
                {"amount_returned": _("Ce champ doit être un booléen (true/false).")}
            )

        reservation.amount_returned = amount_returned
        reservation.save(update_fields=["amount_returned", "date_updated"])
        return Response(
            {"id": reservation.pk, "amount_returned": reservation.amount_returned},
            status=status.HTTP_200_OK,
        )


class ReservationYearsView(APIView):
    """Returns distinct years that have reservations."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        years = (
            Reservation.objects.values_list("check_in__year", flat=True)
            .distinct()
            .order_by("-check_in__year")
        )
        current_year = date.today().year
        year_list = sorted(set(years) | {current_year}, reverse=True)
        return Response({"years": year_list}, status=status.HTTP_200_OK)


class OccupiedDatesView(APIView):
    """Return occupied date ranges for a given apartment."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        apartment_id = request.query_params.get("apartment")
        if not apartment_id:
            return Response([], status=status.HTTP_200_OK)
        exclude_id = request.query_params.get("exclude")
        qs = Reservation.objects.filter(apartment_id=apartment_id).values_list(
            "check_in", "check_out"
        )
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        ranges = [
            {"check_in": str(ci), "check_out": str(co)} for ci, co in qs
        ]
        return Response(ranges, status=status.HTTP_200_OK)
