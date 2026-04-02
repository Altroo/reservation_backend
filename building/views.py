from django.http import Http404
from django.utils.translation import gettext_lazy as _, gettext
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import can_create, can_delete, can_update
from building.models import Building
from building.serializers import BuildingSerializer


class BuildingListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request):
        buildings = Building.objects.all().select_related("created_by_user")
        serializer = BuildingSerializer(buildings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def post(request):
        if not can_create(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour créer une résidence.")
            )

        serializer = BuildingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by_user=request.user)
        return Response(
            BuildingSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


class BuildingDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _get_building(pk: int) -> Building:
        try:
            return Building.objects.select_related("created_by_user").get(pk=pk)
        except Building.DoesNotExist:
            raise Http404(_("Résidence introuvable."))

    def get(self, request, pk: int):
        building = self._get_building(pk)
        return Response(BuildingSerializer(building).data, status=status.HTTP_200_OK)

    def put(self, request, pk: int):
        if not can_update(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour modifier cette résidence.")
            )

        building = self._get_building(pk)
        serializer = BuildingSerializer(building, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BuildingSerializer(building).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer cette résidence.")
            )

        building = self._get_building(pk)

        if building.apartments.exists():
            raise ValidationError(
                {
                    "detail": [
                        _(
                            "Impossible de supprimer cette résidence car "
                            "elle contient des appartements."
                        )
                    ]
                }
            )

        if building.locaux.exists():
            raise ValidationError(
                {
                    "detail": [
                        _(
                            "Impossible de supprimer cette résidence car "
                            "elle contient des locaux."
                        )
                    ]
                }
            )

        building.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulkDeleteBuildingView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def delete(request):
        if not can_delete(request.user):
            raise PermissionDenied(
                _("Vous n'avez pas les droits pour supprimer des résidences.")
            )

        ids = request.data.get("ids", [])
        if not ids or not isinstance(ids, list):
            raise ValidationError({"ids": [_("Une liste d'identifiants est requise.")]})

        qs = Building.objects.filter(id__in=ids)
        with_refs = (
            qs.filter(apartments__isnull=False)
            .distinct()
            .union(qs.filter(locaux__isnull=False).distinct())
        ).count()
        deletable = qs.exclude(
            id__in=qs.filter(apartments__isnull=False)
            .values_list("id", flat=True)
            .union(qs.filter(locaux__isnull=False).values_list("id", flat=True))
        )
        deleted_count = deletable.count()
        deletable.delete()

        msg = gettext("%(count)d résidence(s) supprimée(s).") % {"count": deleted_count}
        if with_refs:
            msg += " " + gettext("%(count)d résidence(s) ignorée(s) (contiennent des appartements ou locaux).") % {"count": with_refs}

        return Response({"detail": msg}, status=status.HTTP_200_OK)
