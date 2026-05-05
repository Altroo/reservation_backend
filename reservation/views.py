from decimal import Decimal
from datetime import date

from django.db import transaction
from django.db.models import Sum, Count
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from building.models import Building
from core.pagination import CustomPagination
from core.permissions import (
    can_access_hilton_reports,
    can_create,
    can_update,
    can_delete,
)
from .filters import ReservationFilter
from .models import (
    Apartment,
    Cost,
    CostCategoryOption,
    HiltonReport,
    HiltonReportApartmentRevenue,
    HiltonReportManualLine,
    PaymentSourceOption,
    Reservation,
)
from .serializers import (
    ApartmentSerializer,
    CostSerializer,
    CostCategoryOptionSerializer,
    HiltonReportMutationSerializer,
    HiltonReportSerializer,
    PaymentSourceOptionSerializer,
    ReservationListSerializer,
    ReservationSerializer,
)


HILTON_BUILDING_NAME = "Hilton residence"


class ApartmentListView(APIView):
    """GET all active apartments, POST create a new apartment."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        apartments = Apartment.objects.all()
        serializer = ApartmentSerializer(apartments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        nom = request.data.get("nom", "").strip()
        if not nom:
            raise ValidationError({"nom": [_("Ce champ est requis.")]})
        if Apartment.objects.filter(nom=nom).exists():
            raise ValidationError(
                {"nom": [_("Un appartement avec ce nom existe déjà.")]}
            )

        building = None
        if "building" in request.data:
            building_value = request.data.get("building")
            if building_value not in (None, ""):
                try:
                    building = Building.objects.get(pk=building_value)
                except (Building.DoesNotExist, TypeError, ValueError):
                    raise ValidationError({"building": [_("Résidence introuvable.")]})

        apartment = Apartment.objects.create(nom=nom, building=building)
        serializer = ApartmentSerializer(apartment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ApartmentDetailView(APIView):
    """PUT rename, DELETE an apartment."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_apartment(pk: int) -> Apartment:
        try:
            return Apartment.objects.get(pk=pk)
        except Apartment.DoesNotExist:
            raise Http404(_("Appartement introuvable."))

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier cet appartement.")
            )
        apartment = self._get_apartment(pk)
        nom = request.data.get("nom", "").strip()
        if not nom:
            raise ValidationError({"nom": [_("Ce champ est requis.")]})
        if Apartment.objects.filter(nom=nom).exclude(pk=pk).exists():
            raise ValidationError(
                {"nom": [_("Un appartement avec ce nom existe déjà.")]}
            )
        apartment.nom = nom
        if "building" in request.data:
            building_val = request.data["building"]
            apartment.building_id = building_val if building_val else None
        apartment.save()
        return Response(ApartmentSerializer(apartment).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer cet appartement.")
            )
        apartment = self._get_apartment(pk)
        if apartment.reservations.exists():
            raise ValidationError(
                {
                    "detail": [
                        _(
                            "Impossible de supprimer cet appartement car il possède des réservations. "
                            "Veuillez d'abord supprimer les réservations associées."
                        )
                    ]
                }
            )
        apartment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentSourceOptionListView(APIView):
    """GET all payment sources, POST create a new payment source."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        serializer = PaymentSourceOptionSerializer(
            PaymentSourceOption.objects.all(), many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        if not can_create(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour créer une source de paiement.")
            )
        serializer = PaymentSourceOptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            PaymentSourceOptionSerializer(instance).data, status=status.HTTP_201_CREATED
        )


class PaymentSourceOptionDetailView(APIView):
    """PUT rename, DELETE a payment source option."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_payment_source(pk: int) -> PaymentSourceOption:
        try:
            return PaymentSourceOption.objects.get(pk=pk)
        except PaymentSourceOption.DoesNotExist:
            raise Http404(_("Source de paiement introuvable."))

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier cette source de paiement.")
            )
        option = self._get_payment_source(pk)
        old_name = option.nom
        serializer = PaymentSourceOptionSerializer(option, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if old_name != instance.nom:
            Reservation.objects.filter(payment_source=old_name).update(
                payment_source=instance.nom
            )
        return Response(
            PaymentSourceOptionSerializer(instance).data, status=status.HTTP_200_OK
        )

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer cette source de paiement.")
            )
        option = self._get_payment_source(pk)
        if Reservation.objects.filter(payment_source=option.nom).exists():
            raise ValidationError(
                {
                    "detail": [
                        _(
                            "Impossible de supprimer cette source de paiement car elle est utilisée par des réservations."
                        )
                    ]
                }
            )
        option.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CostCategoryOptionListView(APIView):
    """GET all cost categories, POST create a new cost category."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        serializer = CostCategoryOptionSerializer(
            CostCategoryOption.objects.all(), many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        if not can_create(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour créer une catégorie de coût.")
            )
        serializer = CostCategoryOptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            CostCategoryOptionSerializer(instance).data, status=status.HTTP_201_CREATED
        )


class CostCategoryOptionDetailView(APIView):
    """PUT rename, DELETE a cost category option."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_cost_category(pk: int) -> CostCategoryOption:
        try:
            return CostCategoryOption.objects.get(pk=pk)
        except CostCategoryOption.DoesNotExist:
            raise Http404(_("Catégorie de coût introuvable."))

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier cette catégorie de coût.")
            )
        option = self._get_cost_category(pk)
        old_name = option.nom
        serializer = CostCategoryOptionSerializer(option, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if old_name != instance.nom:
            Cost.objects.filter(category=old_name).update(category=instance.nom)
        return Response(
            CostCategoryOptionSerializer(instance).data, status=status.HTTP_200_OK
        )

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer cette catégorie de coût.")
            )
        option = self._get_cost_category(pk)
        if Cost.objects.filter(category=option.nom).exists():
            raise ValidationError(
                {
                    "detail": [
                        _(
                            "Impossible de supprimer cette catégorie de coût car elle est utilisée par des coûts."
                        )
                    ]
                }
            )
        option.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        building_id = request.query_params.get("building")
        if building_id:
            qs = qs.filter(apartment__building_id=building_id)
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
            qs.values("apartment__nom")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("apartment__nom")
        )

        # Occupancy: occupied days per apartment per month
        apt_qs = Apartment.objects.all()
        if building_id:
            apt_qs = apt_qs.filter(building_id=building_id)
        apartments = list(apt_qs.values("id", "nom"))
        occupancy_by_apt = {}
        for apt in apartments:
            apt_qs = qs.filter(apartment_id=apt["id"])
            occupied_days = sum(r.nights for r in apt_qs) if apt_qs.exists() else 0
            occupancy_by_apt[apt["nom"]] = {
                "nom": apt["nom"],
                "occupied_days": occupied_days,
                "reservation_count": apt_qs.count(),
                "revenue": float(apt_qs.aggregate(t=Sum("amount"))["t"] or 0),
            }

        # Daily revenue (grouped by check_in date)
        daily = qs.values("check_in").annotate(total=Sum("amount")).order_by("check_in")
        daily_revenue = [
            {"date": str(d["check_in"]), "total": float(d["total"] or 0)} for d in daily
        ]

        # Costs and net profit
        cost_qs = Cost.objects.filter(date__year=year)
        annual_costs = float(cost_qs.aggregate(total=Sum("amount"))["total"] or 0)
        net_profit = float(total_revenue) - annual_costs

        return Response(
            {
                "year": year,
                "total_revenue": float(total_revenue),
                "annual_costs": annual_costs,
                "net_profit": net_profit,
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
                        "nom": item["apartment__nom"],
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
            .select_related("apartment", "apartment__building")
            .order_by("apartment__nom", "check_in")
        )

        building_id = request.query_params.get("building")
        if building_id:
            qs = qs.filter(apartment__building_id=building_id)

        apt_qs = Apartment.objects.all().order_by("nom")
        if building_id:
            apt_qs = apt_qs.filter(building_id=building_id)
        apartments = list(apt_qs)

        result = {}
        for apt in apartments:
            apt_reservations = [r for r in qs if r.apartment_id == apt.id]
            result[apt.nom] = {
                "id": apt.id,
                "nom": apt.nom,
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

        building_id = request.query_params.get("building")
        if building_id:
            qs = qs.filter(apartment__building_id=building_id)

        apt_qs_filter = Apartment.objects.all()
        if building_id:
            apt_qs_filter = apt_qs_filter.filter(building_id=building_id)
        apartments = list(apt_qs_filter.order_by("nom"))

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
            matrix[apt.nom] = {
                "nom": apt.nom,
                "monthly": monthly,
                "year_total": year_total,
            }

        # Returned vs not-returned breakdown
        total_returned = sum(float(r.amount) for r in qs if r.amount_returned)
        total_not_returned = sum(float(r.amount) for r in qs if not r.amount_returned)

        # Individual reservations for the detail table
        reservations = [
            {
                "id": r.id,
                "apartment_nom": r.apartment.nom,
                "guest_name": r.guest_name,
                "check_in": str(r.check_in),
                "check_out": str(r.check_out),
                "amount": float(r.amount),
                "payment_source": r.payment_source,
                "amount_returned": r.amount_returned,
            }
            for r in qs.order_by("apartment__nom", "check_in")
        ]

        return Response(
            {
                "year": year,
                "apartments": matrix,
                "total_returned": total_returned,
                "total_not_returned": total_not_returned,
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
        ranges = [{"check_in": str(ci), "check_out": str(co)} for ci, co in qs]
        return Response(ranges, status=status.HTTP_200_OK)


class HiltonReportBaseView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _require_hilton_access(request):
        if not can_access_hilton_reports(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour accéder aux rapports Hilton.")
            )

    @staticmethod
    def _get_hilton_building() -> Building:
        building = Building.objects.filter(nom__iexact=HILTON_BUILDING_NAME).first()
        if not building:
            raise ValidationError(
                {"detail": _("La résidence Hilton residence est introuvable.")}
            )
        return building

    @staticmethod
    def _latest_report(lock: bool = False):
        qs = HiltonReport.objects.order_by("-end_date", "-id")
        if lock:
            qs = qs.select_for_update()
        return qs.first()

    def _resolve_period(self, start_date, end_date, lock_latest: bool = False):
        if not end_date:
            raise ValidationError({"end_date": [_("Ce champ est requis.")]})

        latest_report = self._latest_report(lock=lock_latest)
        if latest_report:
            resolved_start = latest_report.end_date
        else:
            if not start_date:
                raise ValidationError({"start_date": [_("Ce champ est requis.")]})
            resolved_start = start_date

        if end_date <= resolved_start:
            raise ValidationError(
                {"end_date": [_("La date de fin doit être postérieure à la date de début.")]}
            )
        return resolved_start, end_date

    @staticmethod
    def _build_apartment_rows(building: Building, start_date, end_date):
        apartments = list(Apartment.objects.filter(building=building).order_by("nom"))
        revenue_map = {
            row["apartment_id"]: row
            for row in Reservation.objects.filter(
                apartment__building=building,
                check_in__gte=start_date,
                check_in__lt=end_date,
            )
            .values("apartment_id")
            .annotate(total=Sum("amount"), count=Count("id"))
        }

        rows = []
        for apartment in apartments:
            revenue = revenue_map.get(apartment.id, {})
            rows.append(
                {
                    "apartment": apartment.id,
                    "apartment_nom": apartment.nom,
                    "reservation_count": revenue.get("count", 0),
                    "total_amount": revenue.get("total") or Decimal("0.00"),
                }
            )
        return rows

    @staticmethod
    def _serialize_preview_rows(rows):
        return [
            {
                "apartment": row["apartment"],
                "apartment_nom": row["apartment_nom"],
                "reservation_count": row["reservation_count"],
                "total_amount": str(row["total_amount"]),
            }
            for row in rows
        ]

    @staticmethod
    def _replace_manual_lines(report: HiltonReport, manual_lines):
        report.manual_lines.all().delete()
        HiltonReportManualLine.objects.bulk_create(
            [
                HiltonReportManualLine(
                    report=report,
                    line_type=line.get("line_type", HiltonReportManualLine.LineType.COST),
                    description=line.get("description", "").strip(),
                    amount=(
                        Decimal("0.00")
                        if line.get("line_type") == HiltonReportManualLine.LineType.NOTE
                        else line.get("amount", Decimal("0.00"))
                    ),
                    sort_order=line.get("sort_order", index),
                )
                for index, line in enumerate(manual_lines)
            ]
        )

    @staticmethod
    def _get_report(pk: int) -> HiltonReport:
        try:
            return (
                HiltonReport.objects.select_related("created_by_user")
                .prefetch_related("apartment_revenues", "manual_lines")
                .get(pk=pk)
            )
        except HiltonReport.DoesNotExist:
            raise Http404(_("Rapport Hilton introuvable."))


class HiltonReportListCreateView(HiltonReportBaseView):
    def get(self, request):
        self._require_hilton_access(request)
        reports = (
            HiltonReport.objects.select_related("created_by_user")
            .prefetch_related("apartment_revenues", "manual_lines")
            .order_by("-end_date", "-id")
        )
        return Response(
            HiltonReportSerializer(reports, many=True).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        self._require_hilton_access(request)
        serializer = HiltonReportMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            building = self._get_hilton_building()
            start_date, end_date = self._resolve_period(
                data.get("start_date"),
                data.get("end_date"),
                lock_latest=True,
            )
            report = HiltonReport.objects.create(
                start_date=start_date,
                end_date=end_date,
                notes=data.get("notes", ""),
                created_by_user=request.user,
            )
            rows = self._build_apartment_rows(building, start_date, end_date)
            HiltonReportApartmentRevenue.objects.bulk_create(
                [
                    HiltonReportApartmentRevenue(
                        report=report,
                        apartment_id=row["apartment"],
                        apartment_nom=row["apartment_nom"],
                        reservation_count=row["reservation_count"],
                        total_amount=row["total_amount"],
                    )
                    for row in rows
                ]
            )
            self._replace_manual_lines(report, data.get("manual_lines", []))
            report.recalculate_totals()

        return Response(
            HiltonReportSerializer(self._get_report(report.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class HiltonReportDetailView(HiltonReportBaseView):
    def get(self, request, pk: int):
        self._require_hilton_access(request)
        return Response(
            HiltonReportSerializer(self._get_report(pk)).data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, pk: int):
        self._require_hilton_access(request)
        if "start_date" in request.data or "end_date" in request.data:
            raise ValidationError(
                {"detail": _("La période d'un rapport Hilton ne peut pas être modifiée.")}
            )

        report = self._get_report(pk)
        serializer = HiltonReportMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            report.notes = data.get("notes", report.notes)
            report.save(update_fields=["notes", "date_updated"])
            if "manual_lines" in data:
                self._replace_manual_lines(report, data.get("manual_lines", []))
            report.recalculate_totals()

        return Response(
            HiltonReportSerializer(self._get_report(pk)).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        self._require_hilton_access(request)
        report = self._get_report(pk)
        latest_report = self._latest_report()
        if not latest_report or latest_report.pk != report.pk:
            raise ValidationError(
                {"detail": _("Seul le dernier rapport Hilton peut être supprimé.")}
            )
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HiltonReportPreviewView(HiltonReportBaseView):
    def get(self, request):
        self._require_hilton_access(request)
        serializer = HiltonReportMutationSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        building = self._get_hilton_building()
        start_date, end_date = self._resolve_period(
            data.get("start_date"),
            data.get("end_date"),
        )
        rows = self._build_apartment_rows(building, start_date, end_date)
        gross_revenue = sum(
            (row["total_amount"] for row in rows), Decimal("0.00")
        )

        return Response(
            {
                "building_name": HILTON_BUILDING_NAME,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "gross_revenue": str(gross_revenue),
                "manual_cost_total": "0.00",
                "manual_adjustment_total": "0.00",
                "net_total": str(gross_revenue),
                "apartment_revenues": self._serialize_preview_rows(rows),
            },
            status=status.HTTP_200_OK,
        )


class CostListCreateView(APIView):
    """GET all costs (optionally filtered by year), POST create a new cost."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        building = request.query_params.get("building")
        qs = Cost.objects.select_related("created_by_user", "building").all()
        if year:
            try:
                qs = qs.filter(date__year=int(year))
            except (ValueError, TypeError):
                raise ValidationError({"year": _("year doit être un entier valide.")})
        if month:
            try:
                m = int(month)
                if m < 1 or m > 12:
                    raise ValueError
                qs = qs.filter(date__month=m)
            except (ValueError, TypeError):
                raise ValidationError(
                    {"month": _("month doit être un entier valide entre 1 et 12.")}
                )
        if building:
            try:
                qs = qs.filter(building_id=int(building))
            except (ValueError, TypeError):
                raise ValidationError(
                    {"building": _("building doit être un entier valide.")}
                )
        serializer = CostSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        if not can_create(request.user):
            raise PermissionDenied(_("Vous n'avez pas les droits pour créer un coût."))
        serializer = CostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by_user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CostDetailView(APIView):
    """PUT update or DELETE a single cost."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_cost(pk: int) -> Cost:
        try:
            return Cost.objects.get(pk=pk)
        except Cost.DoesNotExist:
            raise Http404(_("Coût introuvable."))

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier ce coût.")
            )
        cost = self._get_cost(pk)
        serializer = CostSerializer(cost, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer ce coût.")
            )
        self._get_cost(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CostYearsView(APIView):
    """Returns distinct years that have costs, always including the current year."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        years = (
            Cost.objects.values_list("date__year", flat=True)
            .distinct()
            .order_by("-date__year")
        )
        current_year = date.today().year
        year_list = sorted(set(years) | {current_year}, reverse=True)
        return Response({"years": year_list}, status=status.HTTP_200_OK)


class BulkDeleteCostView(APIView):
    """DELETE multiple costs by id list."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def delete(request):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer des coûts.")
            )
        ids = request.data.get("ids", [])
        if not ids or not isinstance(ids, list):
            raise ValidationError({"ids": _("Une liste d'identifiants est requise.")})
        Cost.objects.filter(pk__in=ids).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
