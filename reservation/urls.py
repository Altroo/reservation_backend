from django.urls import path
from .views import (
    ApartmentListView,
    CostDetailView,
    CostListCreateView,
    CostYearsView,
    ReservationListCreateView,
    ReservationDetailEditDeleteView,
    BulkDeleteReservationView,
    DashboardStatsView,
    PlanningMonthView,
    BalanceView,
    ToggleAmountReturnedView,
    ReservationYearsView,
    OccupiedDatesView,
)

urlpatterns = [
    # Apartments
    path("apartments/", ApartmentListView.as_view(), name="apartment-list"),
    # Reservations
    path("", ReservationListCreateView.as_view(), name="reservation-list-create"),
    path(
        "<int:pk>/",
        ReservationDetailEditDeleteView.as_view(),
        name="reservation-detail",
    ),
    path(
        "bulk-delete/",
        BulkDeleteReservationView.as_view(),
        name="reservation-bulk-delete",
    ),
    # Dashboard & analytics
    path("dashboard/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("planning/", PlanningMonthView.as_view(), name="planning-month"),
    path("balance/", BalanceView.as_view(), name="balance"),
    path(
        "<int:pk>/toggle-returned/",
        ToggleAmountReturnedView.as_view(),
        name="toggle-returned",
    ),
    path("years/", ReservationYearsView.as_view(), name="reservation-years"),
    path("occupied-dates/", OccupiedDatesView.as_view(), name="occupied-dates"),
    # Costs
    path("costs/years/", CostYearsView.as_view(), name="cost-years"),
    path("costs/", CostListCreateView.as_view(), name="cost-list-create"),
    path("costs/<int:pk>/", CostDetailView.as_view(), name="cost-detail"),
]
