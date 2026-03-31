from django.urls import path

from building.views import (
    BuildingDetailView,
    BuildingListCreateView,
    BulkDeleteBuildingView,
)

urlpatterns = [
    path("buildings/", BuildingListCreateView.as_view(), name="building-list-create"),
    path(
        "buildings/<int:pk>/",
        BuildingDetailView.as_view(),
        name="building-detail",
    ),
    path(
        "buildings/bulk-delete/",
        BulkDeleteBuildingView.as_view(),
        name="building-bulk-delete",
    ),
]
