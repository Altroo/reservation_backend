from datetime import date, timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from account.models import CustomUser
from building.models import Building
from reservation.models import Apartment, Cost, Reservation

pytestmark = pytest.mark.django_db


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_staff_user(email="staff@test.com", password="securepass123"):
    """Staff user with all permissions."""
    user = CustomUser.objects.create_user(
        email=email,
        password=password,
        is_staff=True,
        can_create=True,
        can_edit=True,
        can_delete=True,
        can_view=True,
    )
    token = str(AccessToken.for_user(user))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return user, client


def make_readonly_user(email="readonly@test.com", password="securepass123"):
    """Read-only user — no write permissions."""
    user = CustomUser.objects.create_user(
        email=email,
        password=password,
        is_staff=False,
        can_create=False,
        can_edit=False,
        can_delete=False,
        can_view=True,
    )
    token = str(AccessToken.for_user(user))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return user, client


def make_apartment(nom="5B"):
    return Apartment.objects.create(nom=nom)


def make_building(nom="Residence Test"):
    return Building.objects.create(nom=nom)


def make_reservation(apartment, created_by=None, **kwargs):
    defaults = {
        "guest_name": "Alice Martin",
        "check_in": date(2025, 1, 10),
        "check_out": date(2025, 1, 15),
        "amount": "500.00",
        "payment_source": "Cash",
    }
    defaults.update(kwargs)
    return Reservation.objects.create(
        apartment=apartment,
        created_by_user=created_by,
        **defaults,
    )


# ── Model Tests ───────────────────────────────────────────────────────────────


class TestApartmentModel:
    def test_str(self):
        apt = Apartment(nom="5B")
        assert str(apt) == "5B"

    def test_unique_nom(self):
        from django.db import IntegrityError

        make_apartment(nom="UNQ")
        with pytest.raises(IntegrityError):
            make_apartment(nom="UNQ")


class TestReservationModel:
    def test_str(self):
        apt = make_apartment(nom="5B")
        user, _ = make_staff_user()
        r = make_reservation(apt, created_by=user, guest_name="Bob")
        assert "5B" in str(r) and "Bob" in str(r)

    def test_nights_property(self):
        apt = make_apartment(nom="N1")
        r = make_reservation(
            apt,
            check_in=date(2025, 3, 1),
            check_out=date(2025, 3, 5),
        )
        assert r.nights == 4

    def test_checkout_after_checkin_valid(self):
        # No error expected
        apt = make_apartment(nom="V1")
        r = make_reservation(apt, check_in=date(2025, 4, 1), check_out=date(2025, 4, 2))
        assert r.pk is not None

    def test_payment_source_choices(self):
        apt = make_apartment(nom="PS")
        for src in ("Booking", "Airbnb", "Cash", "Bank"):
            r = make_reservation(
                apt,
                payment_source=src,
                check_in=date(2025, 5, 1),
                check_out=date(2025, 5, 2),
            )
            assert r.payment_source == src


# ── Apartment API ─────────────────────────────────────────────────────────────


class TestApartmentListView:
    def setup_method(self):
        self.url = reverse("reservation:apartment-list")
        self.staff_user, self.staff_client = make_staff_user()
        self.anon_client = APIClient()

    def test_list_apartments_returns_200(self):
        make_apartment(nom="AP1")
        make_apartment(nom="AP2")
        response = self.staff_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        noms = [a["nom"] for a in response.data]
        assert "AP1" in noms
        assert "AP2" in noms

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_apartment_with_building_returns_201(self):
        building = make_building(nom="Residence AP")

        response = self.staff_client.post(
            self.url,
            {"nom": "AP3", "building": building.pk},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["building"] == building.pk
        assert Apartment.objects.get(nom="AP3").building_id == building.pk

    def test_create_apartment_with_unknown_building_returns_400(self):
        response = self.staff_client.post(
            self.url,
            {"nom": "AP4", "building": 99999},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "building" in response.data["details"]


# ── Reservation List/Create ───────────────────────────────────────────────────


class TestReservationListCreateView:
    def setup_method(self):
        self.url = reverse("reservation:reservation-list-create")
        self.staff_user, self.staff_client = make_staff_user()
        self.readonly_user, self.readonly_client = make_readonly_user()
        self.anon_client = APIClient()
        self.apt = make_apartment(nom="LC")

    def test_list_returns_200(self):
        make_reservation(self.apt, created_by=self.staff_user)
        response = self.staff_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_list_paginated(self):
        for i in range(3):
            make_reservation(
                self.apt,
                created_by=self.staff_user,
                check_in=date(2025, 1, i + 1),
                check_out=date(2025, 1, i + 2),
            )
        response = self.staff_client.get(self.url, {"pagination": "true", "page": 1})
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data

    def test_list_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_returns_201(self):
        payload = {
            "apartment": self.apt.pk,
            "guest_name": "Jean Dupont",
            "check_in": "2025-06-01",
            "check_out": "2025-06-05",
            "amount": "400.00",
            "payment_source": "Booking",
        }
        response = self.staff_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["guest_name"] == "Jean Dupont"
        assert response.data["nights"] == 4

    def test_create_without_permission_returns_403(self):
        payload = {
            "apartment": self.apt.pk,
            "guest_name": "Refus",
            "check_in": "2025-06-10",
            "check_out": "2025-06-12",
            "amount": "200.00",
            "payment_source": "Cash",
        }
        response = self.readonly_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_unauthenticated_returns_401(self):
        response = self.anon_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_checkout_before_checkin_returns_400(self):
        payload = {
            "apartment": self.apt.pk,
            "guest_name": "Bad Dates",
            "check_in": "2025-06-10",
            "check_out": "2025-06-08",
            "amount": "200.00",
            "payment_source": "Cash",
        }
        response = self.staff_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_missing_required_field_returns_400(self):
        payload = {
            "guest_name": "Missing Apartment",
            "check_in": "2025-06-10",
            "check_out": "2025-06-12",
        }
        response = self.staff_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_by_payment_source(self):
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            payment_source="Airbnb",
            check_in=date(2025, 7, 1),
            check_out=date(2025, 7, 3),
        )
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            payment_source="Cash",
            check_in=date(2025, 7, 4),
            check_out=date(2025, 7, 6),
        )
        response = self.staff_client.get(self.url, {"payment_source": "Airbnb"})
        assert response.status_code == status.HTTP_200_OK
        for item in response.data:
            assert item["payment_source"] == "Airbnb"

    def test_filter_by_year_month(self):
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 3, 5),
            check_out=date(2025, 3, 7),
        )
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 4, 5),
            check_out=date(2025, 4, 7),
        )
        response = self.staff_client.get(self.url, {"year": 2025, "month": 3})
        assert response.status_code == status.HTTP_200_OK
        for item in response.data:
            assert item["check_in"][:7] == "2025-03"


# ── Reservation Detail/Edit/Delete ────────────────────────────────────────────


class TestReservationDetailEditDeleteView:
    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user()
        self.readonly_user, self.readonly_client = make_readonly_user()
        self.anon_client = APIClient()
        self.apt = make_apartment(nom="DED")
        self.reservation = make_reservation(self.apt, created_by=self.staff_user)
        self.url = reverse(
            "reservation:reservation-detail", kwargs={"pk": self.reservation.pk}
        )

    def test_get_returns_200(self):
        response = self.staff_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.reservation.pk

    def test_get_not_found_returns_404(self):
        url = reverse("reservation:reservation-detail", kwargs={"pk": 99999})
        response = self.staff_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_put_updates_reservation(self):
        payload = {
            "apartment": self.apt.pk,
            "guest_name": "Updated Guest",
            "check_in": "2025-02-01",
            "check_out": "2025-02-05",
            "amount": "750.00",
            "payment_source": "Bank",
        }
        response = self.staff_client.put(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["guest_name"] == "Updated Guest"
        assert response.data["payment_source"] == "Bank"

    def test_put_without_permission_returns_403(self):
        payload = {
            "apartment": self.apt.pk,
            "guest_name": "Blocked",
            "check_in": "2025-02-01",
            "check_out": "2025-02-03",
            "amount": "200.00",
            "payment_source": "Cash",
        }
        response = self.readonly_client.put(self.url, payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_returns_204(self):
        response = self.staff_client.delete(self.url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Reservation.objects.filter(pk=self.reservation.pk).exists()

    def test_delete_without_permission_returns_403(self):
        response = self.readonly_client.delete(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_unauthenticated_returns_401(self):
        response = self.anon_client.delete(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── Bulk Delete ───────────────────────────────────────────────────────────────


class TestBulkDeleteReservationView:
    def setup_method(self):
        self.url = reverse("reservation:reservation-bulk-delete")
        self.staff_user, self.staff_client = make_staff_user()
        self.readonly_user, self.readonly_client = make_readonly_user()
        self.apt = make_apartment(nom="BD")

    def test_bulk_delete_returns_204(self):
        r1 = make_reservation(
            self.apt, check_in=date(2025, 8, 1), check_out=date(2025, 8, 3)
        )
        r2 = make_reservation(
            self.apt, check_in=date(2025, 8, 5), check_out=date(2025, 8, 7)
        )
        response = self.staff_client.delete(
            self.url, {"ids": [r1.pk, r2.pk]}, format="json"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Reservation.objects.filter(pk__in=[r1.pk, r2.pk]).exists()

    def test_bulk_delete_without_permission_returns_403(self):
        r = make_reservation(
            self.apt, check_in=date(2025, 9, 1), check_out=date(2025, 9, 2)
        )
        response = self.readonly_client.delete(self.url, {"ids": [r.pk]}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_delete_empty_ids_returns_400(self):
        response = self.staff_client.delete(self.url, {"ids": []}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_delete_missing_ids_returns_400(self):
        response = self.staff_client.delete(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ── Dashboard Stats ───────────────────────────────────────────────────────────


class TestDashboardStatsView:
    def setup_method(self):
        self.url = reverse("reservation:dashboard-stats")
        self.staff_user, self.staff_client = make_staff_user()
        self.anon_client = APIClient()
        self.apt = make_apartment(nom="DS")
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 1, 1),
            check_out=date(2025, 1, 5),
            amount="400.00",
            payment_source="Cash",
        )
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 3, 10),
            check_out=date(2025, 3, 15),
            amount="600.00",
            payment_source="Airbnb",
        )

    def test_returns_200(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert response.status_code == status.HTTP_200_OK

    def test_total_revenue(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert response.data["total_revenue"] == pytest.approx(1000.0)

    def test_monthly_revenue_has_12_months(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert len(response.data["monthly_revenue"]) == 12

    def test_by_source_present(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        sources = [s["source"] for s in response.data["by_source"]]
        assert "Cash" in sources
        assert "Airbnb" in sources

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url, {"year": 2025})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_year_returns_400(self):
        response = self.staff_client.get(self.url, {"year": "abc"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_daily_revenue_present(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert "daily_revenue" in response.data
        daily = response.data["daily_revenue"]
        assert isinstance(daily, list)
        assert len(daily) >= 2
        dates = [d["date"] for d in daily]
        assert "2025-01-01" in dates
        assert "2025-03-10" in dates

    def test_daily_revenue_totals(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        daily = {d["date"]: d["total"] for d in response.data["daily_revenue"]}
        assert daily["2025-01-01"] == pytest.approx(400.0)
        assert daily["2025-03-10"] == pytest.approx(600.0)


# ── Planning ──────────────────────────────────────────────────────────────────


class TestPlanningMonthView:
    def setup_method(self):
        self.url = reverse("reservation:planning-month")
        self.staff_user, self.staff_client = make_staff_user()
        self.anon_client = APIClient()
        self.apt = make_apartment(nom="PL")

    def test_returns_200_with_apartments_key(self):
        response = self.staff_client.get(self.url, {"year": 2025, "month": 6})
        assert response.status_code == status.HTTP_200_OK
        assert "apartments" in response.data
        assert "last_day" in response.data

    def test_reservation_appears_in_correct_month(self):
        make_reservation(
            self.apt,
            check_in=date(2025, 6, 5),
            check_out=date(2025, 6, 10),
        )
        response = self.staff_client.get(self.url, {"year": 2025, "month": 6})
        assert response.status_code == status.HTTP_200_OK
        apt_data = response.data["apartments"].get("PL")
        assert apt_data is not None
        assert len(apt_data["reservations"]) >= 1

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url, {"year": 2025, "month": 6})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_month_returns_400(self):
        response = self.staff_client.get(self.url, {"year": 2025, "month": "xyz"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ── Balance ───────────────────────────────────────────────────────────────────


class TestBalanceView:
    def setup_method(self):
        self.url = reverse("reservation:balance")
        self.staff_user, self.staff_client = make_staff_user()
        self.anon_client = APIClient()
        self.apt = make_apartment(nom="BV")

    def test_returns_200(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert response.status_code == status.HTTP_200_OK

    def test_structure_has_apartments_key(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert "apartments" in response.data
        assert "total_returned" in response.data
        assert "total_not_returned" in response.data
        assert "reservations" in response.data


def make_cost(user, year=2025, **kwargs):
    defaults = {
        "description": "Test cost",
        "amount": "200.00",
        "date": date(year, 6, 15),
        "category": "Autre",
        "building": None,
    }
    defaults.update(kwargs)
    return Cost.objects.create(created_by_user=user, **defaults)


# ── Cost API ─────────────────────────────────────────────────────────────────


class TestCostListCreateView:
    def setup_method(self):
        self.url = reverse("reservation:cost-list-create")
        self.staff_user, self.staff_client = make_staff_user(email="costs@test.com")
        self.readonly_user, self.readonly_client = make_readonly_user(
            email="costs-readonly@test.com"
        )
        self.anon_client = APIClient()

    def test_list_filters_by_building(self):
        building_a = make_building(nom="Residence A")
        building_b = make_building(nom="Residence B")
        make_cost(self.staff_user, year=2025, building=building_a, description="A")
        make_cost(self.staff_user, year=2025, building=building_b, description="B")

        response = self.staff_client.get(self.url, {"building": building_a.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["building"] == building_a.pk
        assert response.data[0]["building_nom"] == "Residence A"

    def test_create_with_building_returns_201(self):
        building = make_building(nom="Residence Cost")

        response = self.staff_client.post(
            self.url,
            {
                "description": "Internet",
                "amount": "350.00",
                "date": "2025-06-15",
                "category": "Charges",
                "building": building.pk,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["building"] == building.pk
        assert response.data["building_nom"] == building.nom
        assert Cost.objects.get(description="Internet").building_id == building.pk

    def test_create_without_permission_returns_403(self):
        response = self.readonly_client.post(
            self.url,
            {
                "description": "Blocked",
                "amount": "100.00",
                "date": "2025-06-15",
                "category": "Autre",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCostDetailView:
    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(email="cost-detail@test.com")
        self.readonly_user, self.readonly_client = make_readonly_user(
            email="cost-detail-readonly@test.com"
        )

    def test_update_building_returns_200(self):
        building = make_building(nom="Residence Cost Update")
        cost = make_cost(self.staff_user, description="Syndic")
        url = reverse("reservation:cost-detail", kwargs={"pk": cost.pk})

        response = self.staff_client.put(
            url,
            {
                "description": "Syndic",
                "amount": "200.00",
                "date": "2025-06-15",
                "category": "Charges",
                "building": building.pk,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["building"] == building.pk
        assert response.data["building_nom"] == building.nom

    def test_update_without_permission_returns_403(self):
        cost = make_cost(self.staff_user)
        url = reverse("reservation:cost-detail", kwargs={"pk": cost.pk})

        response = self.readonly_client.put(
            url,
            {
                "description": "Blocked",
                "amount": "200.00",
                "date": "2025-06-15",
                "category": "Autre",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ── Cost Years ────────────────────────────────────────────────────────────────


class TestCostYearsView:
    def setup_method(self):
        self.url = reverse("reservation:cost-years")
        self.staff_user, self.staff_client = make_staff_user(email="costyears@test.com")
        self.anon_client = APIClient()

    def test_returns_200(self):
        response = self.staff_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_response_has_years_key(self):
        response = self.staff_client.get(self.url)
        assert "years" in response.data

    def test_always_includes_current_year(self):
        response = self.staff_client.get(self.url)
        assert date.today().year in response.data["years"]

    def test_returns_years_with_costs(self):
        make_cost(self.staff_user, year=2023)
        make_cost(self.staff_user, year=2021)
        response = self.staff_client.get(self.url)
        years = response.data["years"]
        assert 2023 in years
        assert 2021 in years

    def test_years_are_sorted_descending(self):
        make_cost(self.staff_user, year=2022)
        make_cost(self.staff_user, year=2024)
        response = self.staff_client.get(self.url)
        years = response.data["years"]
        assert years == sorted(years, reverse=True)

    def test_no_duplicate_years(self):
        make_cost(self.staff_user, year=2024)
        make_cost(self.staff_user, year=2024)
        response = self.staff_client.get(self.url)
        years = response.data["years"]
        assert len(years) == len(set(years))

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestToggleAmountReturnedView:
    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user()
        self.anon_client = APIClient()
        self.apt = make_apartment(nom="TG")
        self.reservation = make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 4, 1),
            check_out=date(2025, 4, 5),
            amount="1000.00",
            payment_source="Airbnb",
        )
        self.url = reverse(
            "reservation:toggle-returned", kwargs={"pk": self.reservation.pk}
        )

    def test_toggle_to_true(self):
        assert self.reservation.amount_returned is False
        response = self.staff_client.patch(
            self.url, {"amount_returned": True}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["amount_returned"] is True
        self.reservation.refresh_from_db()
        assert self.reservation.amount_returned is True

    def test_toggle_to_false(self):
        self.reservation.amount_returned = True
        self.reservation.save()
        response = self.staff_client.patch(
            self.url, {"amount_returned": False}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["amount_returned"] is False
        self.reservation.refresh_from_db()
        assert self.reservation.amount_returned is False

    def test_invalid_value_returns_400(self):
        response = self.staff_client.patch(
            self.url, {"amount_returned": "maybe"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_field_returns_400(self):
        response = self.staff_client.patch(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_not_found_returns_404(self):
        url = reverse("reservation:toggle-returned", kwargs={"pk": 99999})
        response = self.staff_client.patch(
            url, {"amount_returned": True}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.patch(
            self.url, {"amount_returned": True}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── ReservationFilter — new filter params ─────────────────────────────────────


@pytest.mark.django_db
class TestReservationFilterSearch:
    def setup_method(self):
        self.url = reverse("reservation:reservation-list-create")
        self.staff_user, self.staff_client = make_staff_user()
        self.apt = make_apartment(nom="LC")

    def test_search_returns_matching_guest(self):
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            guest_name="Alice Martin",
            check_in=date(2025, 1, 1),
            check_out=date(2025, 1, 3),
        )
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            guest_name="Bob Dupont",
            check_in=date(2025, 2, 1),
            check_out=date(2025, 2, 3),
        )
        response = self.staff_client.get(self.url, {"search": "alice"})
        assert response.status_code == status.HTTP_200_OK
        assert all("alice" in r["guest_name"].lower() for r in response.data)

    def test_search_case_insensitive(self):
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            guest_name="Carlos Lopez",
            check_in=date(2025, 3, 1),
            check_out=date(2025, 3, 4),
        )
        response = self.staff_client.get(self.url, {"search": "CARLOS"})
        assert response.status_code == status.HTTP_200_OK
        assert any("Carlos" in r["guest_name"] for r in response.data)

    def test_search_no_match_returns_empty(self):
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            guest_name="Diana Prince",
            check_in=date(2025, 4, 1),
            check_out=date(2025, 4, 2),
        )
        response = self.staff_client.get(self.url, {"search": "zzznomatch"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


@pytest.mark.django_db
class TestReservationFilterAmount:
    def setup_method(self):
        self.url = reverse("reservation:reservation-list-create")
        self.staff_user, self.staff_client = make_staff_user()
        self.apt = make_apartment(nom="LC")
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            amount=100,
            check_in=date(2025, 1, 1),
            check_out=date(2025, 1, 2),
        )
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            amount=300,
            check_in=date(2025, 2, 1),
            check_out=date(2025, 2, 2),
        )
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            amount=500,
            check_in=date(2025, 3, 1),
            check_out=date(2025, 3, 2),
        )

    def test_amount_exact(self):
        response = self.staff_client.get(self.url, {"amount": 300})
        assert response.status_code == status.HTTP_200_OK
        assert all(float(r["amount"]) == 300 for r in response.data)

    def test_amount_gt(self):
        response = self.staff_client.get(self.url, {"amount__gt": 300})
        assert response.status_code == status.HTTP_200_OK
        assert all(float(r["amount"]) > 300 for r in response.data)

    def test_amount_gte(self):
        response = self.staff_client.get(self.url, {"amount__gte": 300})
        assert response.status_code == status.HTTP_200_OK
        assert all(float(r["amount"]) >= 300 for r in response.data)

    def test_amount_lt(self):
        response = self.staff_client.get(self.url, {"amount__lt": 300})
        assert response.status_code == status.HTTP_200_OK
        assert all(float(r["amount"]) < 300 for r in response.data)

    def test_amount_lte(self):
        response = self.staff_client.get(self.url, {"amount__lte": 300})
        assert response.status_code == status.HTTP_200_OK
        assert all(float(r["amount"]) <= 300 for r in response.data)

    def test_amount_ne(self):
        response = self.staff_client.get(self.url, {"amount__ne": 300})
        assert response.status_code == status.HTTP_200_OK
        assert all(float(r["amount"]) != 300 for r in response.data)
        assert len(response.data) == 2


@pytest.mark.django_db
class TestReservationFilterNights:
    def setup_method(self):
        self.url = reverse("reservation:reservation-list-create")
        self.staff_user, self.staff_client = make_staff_user()
        self.apt = make_apartment(nom="LC")
        # 1 night
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 1, 1),
            check_out=date(2025, 1, 2),
        )
        # 3 nights
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 2, 1),
            check_out=date(2025, 2, 4),
        )
        # 7 nights
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 3, 1),
            check_out=date(2025, 3, 8),
        )

    def test_nights_exact(self):
        response = self.staff_client.get(self.url, {"nights": 3})
        assert response.status_code == status.HTTP_200_OK
        assert all(r["nights"] == 3 for r in response.data)
        assert len(response.data) == 1

    def test_nights_gt(self):
        response = self.staff_client.get(self.url, {"nights__gt": 3})
        assert response.status_code == status.HTTP_200_OK
        assert all(r["nights"] > 3 for r in response.data)
        assert len(response.data) == 1

    def test_nights_gte(self):
        response = self.staff_client.get(self.url, {"nights__gte": 3})
        assert response.status_code == status.HTTP_200_OK
        assert all(r["nights"] >= 3 for r in response.data)
        assert len(response.data) == 2

    def test_nights_lt(self):
        response = self.staff_client.get(self.url, {"nights__lt": 3})
        assert response.status_code == status.HTTP_200_OK
        assert all(r["nights"] < 3 for r in response.data)
        assert len(response.data) == 1

    def test_nights_lte(self):
        response = self.staff_client.get(self.url, {"nights__lte": 3})
        assert response.status_code == status.HTTP_200_OK
        assert all(r["nights"] <= 3 for r in response.data)
        assert len(response.data) == 2
