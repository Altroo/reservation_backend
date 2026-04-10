from django.urls import path

from local.views import (
    BulkDeleteLocalView,
    LocalDashboardView,
    LocalDetailView,
    LocalListCreateView,
    LocalPlanningView,
    LocalTypeOptionDetailView,
    LocalTypeOptionListView,
    LocalYearsView,
    LoyerDetailView,
    LoyerListCreateView,
    LoyerTogglePaidView,
)

urlpatterns = [
    path("types/", LocalTypeOptionListView.as_view(), name="local-type-list"),
    path(
        "types/<int:pk>/", LocalTypeOptionDetailView.as_view(), name="local-type-detail"
    ),
    # Locaux
    path("locaux/", LocalListCreateView.as_view(), name="local-list-create"),
    path("locaux/<int:pk>/", LocalDetailView.as_view(), name="local-detail"),
    path(
        "locaux/bulk-delete/",
        BulkDeleteLocalView.as_view(),
        name="local-bulk-delete",
    ),
    # Loyers
    path("loyers/", LoyerListCreateView.as_view(), name="loyer-list-create"),
    path("loyers/<int:pk>/", LoyerDetailView.as_view(), name="loyer-detail"),
    path(
        "loyers/<int:pk>/toggle-paid/",
        LoyerTogglePaidView.as_view(),
        name="loyer-toggle-paid",
    ),
    # Planning & Dashboard
    path("planning/", LocalPlanningView.as_view(), name="local-planning"),
    path("dashboard/", LocalDashboardView.as_view(), name="local-dashboard"),
    path("years/", LocalYearsView.as_view(), name="local-years"),
]
