from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import CustomPagination
from core.permissions import can_create, can_delete, can_update
from local.filters import LocalFilter, LoyerFilter
from local.models import Local, Loyer
from local.serializers import (
    LocalListSerializer,
    LocalSerializer,
    LoyerListSerializer,
    LoyerSerializer,
)

# ── Local CRUD ────────────────────────────────────────────────────────────────


class LocalListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        pagination = request.query_params.get("pagination", "false").lower() == "true"
        base_qs = Local.objects.all().select_related("created_by_user").order_by("nom")

        filterset = LocalFilter(request.GET, queryset=base_qs)
        qs = filterset.qs

        if pagination:
            paginator = CustomPagination()
            page = paginator.paginate_queryset(qs, request)
            serializer = LocalListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = LocalListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        if not can_create(request.user):
            raise PermissionDenied(_("Vous n'avez pas les droits pour créer un local."))

        serializer = LocalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by_user=request.user)
        return Response(
            LocalListSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


class LocalDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_local(pk: int) -> Local:
        try:
            return Local.objects.select_related("created_by_user").get(pk=pk)
        except Local.DoesNotExist:
            raise Http404(_("Local introuvable."))

    def get(self, request, pk: int):
        local = self._get_local(pk)
        serializer = LocalListSerializer(local)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier ce local.")
            )

        local = self._get_local(pk)
        serializer = LocalSerializer(local, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LocalListSerializer(local).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer ce local.")
            )

        local = self._get_local(pk)

        if local.loyers.exists():
            raise ValidationError(
                {
                    "detail": [
                        _(
                            "Impossible de supprimer ce local car il "
                            "possède des loyers enregistrés."
                        )
                    ]
                }
            )

        local.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulkDeleteLocalView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def delete(request):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer des locaux.")
            )

        ids = request.data.get("ids", [])
        if not ids or not isinstance(ids, list):
            raise ValidationError({"ids": [_("Une liste d'identifiants est requise.")]})

        # Only delete locaux without loyers
        qs = Local.objects.filter(id__in=ids)
        with_loyers = qs.filter(loyers__isnull=False).distinct().count()
        deletable = qs.filter(loyers__isnull=True)
        deleted_count = deletable.count()
        deletable.delete()

        msg = f"{deleted_count} local/locaux supprimé(s)."
        if with_loyers:
            msg += f" {with_loyers} local/locaux ignoré(s) " f"(possèdent des loyers)."

        return Response({"detail": msg}, status=status.HTTP_200_OK)


# ── Loyer CRUD ────────────────────────────────────────────────────────────────


class LoyerListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        base_qs = (
            Loyer.objects.all()
            .select_related("local", "created_by_user")
            .order_by("-annee", "-mois")
        )

        filterset = LoyerFilter(request.GET, queryset=base_qs)
        qs = filterset.qs

        serializer = LoyerListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        if not can_create(request.user):
            raise PermissionDenied(_("Vous n'avez pas les droits pour créer un loyer."))

        serializer = LoyerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by_user=request.user)
        return Response(
            LoyerListSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


class LoyerDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_loyer(pk: int) -> Loyer:
        try:
            return Loyer.objects.select_related("local", "created_by_user").get(pk=pk)
        except Loyer.DoesNotExist:
            raise Http404(_("Loyer introuvable."))

    def get(self, request, pk: int):
        loyer = self._get_loyer(pk)
        serializer = LoyerListSerializer(loyer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier ce loyer.")
            )

        loyer = self._get_loyer(pk)
        serializer = LoyerSerializer(loyer, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LoyerListSerializer(loyer).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer ce loyer.")
            )

        loyer = self._get_loyer(pk)
        loyer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoyerTogglePaidView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def patch(request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier " "le statut de paiement.")
            )

        try:
            loyer = Loyer.objects.select_related("local").get(pk=pk)
        except Loyer.DoesNotExist:
            raise Http404(_("Loyer introuvable."))

        paye = request.data.get("paye")
        if paye is None:
            raise ValidationError({"paye": [_("Le champ 'paye' est requis.")]})

        loyer.paye = bool(paye)
        if loyer.paye and not loyer.date_paiement:
            loyer.date_paiement = date.today()
        elif not loyer.paye:
            loyer.date_paiement = None
        loyer.save()

        return Response(
            {"id": loyer.pk, "paye": loyer.paye},
            status=status.HTTP_200_OK,
        )


# ── Planning ──────────────────────────────────────────────────────────────────


class LocalPlanningView(APIView):
    """Return all locaux with their loyer status for a given year."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        year = request.query_params.get("year", date.today().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            raise ValidationError({"year": _("L'année doit être un entier valide.")})

        locaux = Local.objects.all().order_by("nom")

        building_id = request.query_params.get("building")
        if building_id:
            locaux = locaux.filter(building_id=building_id)

        loyers = Loyer.objects.filter(annee=year).select_related("local")
        if building_id:
            loyers = loyers.filter(local__building_id=building_id)

        # Build a lookup: {local_id: {month: loyer_data}}
        loyer_map: dict[int, dict[int, dict]] = {}
        for loyer in loyers:
            loyer_map.setdefault(loyer.local_id, {})[loyer.mois] = {
                "id": loyer.pk,
                "montant": str(loyer.montant),
                "paye": loyer.paye,
                "date_paiement": (
                    str(loyer.date_paiement) if loyer.date_paiement else None
                ),
            }

        result = []
        for local in locaux:
            months = {}
            for m in range(1, 13):
                loyer_data = loyer_map.get(local.pk, {}).get(m)
                months[m] = loyer_data or None
            result.append(
                {
                    "id": local.pk,
                    "nom": local.nom,
                    "type_local": local.type_local,
                    "en_location": local.en_location,
                    "locataire_nom": local.locataire_nom,
                    "prix_location_mensuel": str(local.prix_location_mensuel),
                    "months": months,
                }
            )

        return Response({"year": year, "locaux": result}, status=status.HTTP_200_OK)


# ── Dashboard ─────────────────────────────────────────────────────────────────


class LocalDashboardView(APIView):
    """Dashboard KPI: total benefit HT, rentabilité per local."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        year = request.query_params.get("year", date.today().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            raise ValidationError({"year": _("L'année doit être un entier valide.")})

        locaux = Local.objects.all().order_by("nom")

        building_id = request.query_params.get("building")
        if building_id:
            locaux = locaux.filter(building_id=building_id)

        # Total benefit HT = sum of paid loyers for the year
        loyer_qs = Loyer.objects.filter(annee=year, paye=True)
        if building_id:
            loyer_qs = loyer_qs.filter(local__building_id=building_id)
        total_benefice = loyer_qs.aggregate(total=Sum("montant"))["total"] or Decimal(
            "0.00"
        )

        # Per-local stats
        locaux_data = []
        total_en_location = 0
        total_libres = 0
        for local in locaux:
            if local.en_location:
                total_en_location += 1
            else:
                total_libres += 1

            loyers_annee = Loyer.objects.filter(local=local, annee=year)
            loyers_payes = loyers_annee.filter(paye=True).aggregate(
                total=Sum("montant")
            )["total"] or Decimal("0.00")
            loyers_impayes = loyers_annee.filter(paye=False).aggregate(
                total=Sum("montant")
            )["total"] or Decimal("0.00")

            locaux_data.append(
                {
                    "id": local.pk,
                    "nom": local.nom,
                    "type_local": local.type_local,
                    "en_location": local.en_location,
                    "prix_achat": str(local.prix_achat),
                    "prix_location_mensuel": str(local.prix_location_mensuel),
                    "rentabilite": str(local.rentabilite),
                    "loyers_payes": str(loyers_payes),
                    "loyers_impayes": str(loyers_impayes),
                }
            )

        return Response(
            {
                "year": year,
                "total_benefice_ht": str(total_benefice),
                "total_en_location": total_en_location,
                "total_libres": total_libres,
                "locaux": locaux_data,
            },
            status=status.HTTP_200_OK,
        )


# ── Years ─────────────────────────────────────────────────────────────────────


class LocalYearsView(APIView):
    """Return distinct years from loyers."""

    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        years = (
            Loyer.objects.values_list("annee", flat=True).distinct().order_by("-annee")
        )
        return Response({"years": list(years)}, status=status.HTTP_200_OK)
