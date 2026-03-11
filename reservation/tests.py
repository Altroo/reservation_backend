from datetime import date, timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from account.models import CustomUser
from reservation.models import Apartment, Reservation

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


def make_apartment(code="5B", name="Hilton City Center 5B", is_active=True):
    return Apartment.objects.create(code=code, name=name, is_active=is_active)


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
        apt = Apartment(code="5B", name="Hilton City Center 5B")
        assert str(apt) == "5B — Hilton City Center 5B"

    def test_unique_code(self):
        from django.db import IntegrityError

        make_apartment(code="UNQ")
        with pytest.raises(IntegrityError):
            make_apartment(code="UNQ")
    def test_monthly_cost_default_is_zero(self):
        apt = make_apartment(code="MC")
        assert apt.monthly_cost == 0

    def test_monthly_cost_set(self):
        apt = Apartment.objects.create(code="MC2", name="Test", monthly_cost="15500.00")
        apt.refresh_from_db()
        assert float(apt.monthly_cost) == 15500.0

class TestReservationModel:
    def test_str(self):
        apt = make_apartment(code="5B")
        user, _ = make_staff_user()
        r = make_reservation(apt, created_by=user, guest_name="Bob")
        assert "5B" in str(r) and "Bob" in str(r)

    def test_nights_property(self):
        apt = make_apartment(code="N1")
        r = make_reservation(
            apt,
            check_in=date(2025, 3, 1),
            check_out=date(2025, 3, 5),
        )
        assert r.nights == 4

    def test_checkout_after_checkin_valid(self):
        # No error expected
        apt = make_apartment(code="V1")
        r = make_reservation(apt, check_in=date(2025, 4, 1), check_out=date(2025, 4, 2))
        assert r.pk is not None

    def test_payment_source_choices(self):
        apt = make_apartment(code="PS")
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
        make_apartment(code="AP1")
        make_apartment(code="AP2")
        response = self.staff_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        codes = [a["code"] for a in response.data]
        assert "AP1" in codes
        assert "AP2" in codes

    def test_apartment_includes_monthly_cost(self):
        Apartment.objects.create(code="MCT", name="Test", monthly_cost="15500.00")
        response = self.staff_client.get(self.url)
        apt = next(a for a in response.data if a["code"] == "MCT")
        assert apt["monthly_cost"] == "15500.00"

    def test_inactive_apartments_excluded(self):
        make_apartment(code="ACT", is_active=True)
        make_apartment(code="INA", is_active=False)
        response = self.staff_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        codes = [a["code"] for a in response.data]
        assert "ACT" in codes
        assert "INA" not in codes

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── Reservation List/Create ───────────────────────────────────────────────────


class TestReservationListCreateView:
    def setup_method(self):
        self.url = reverse("reservation:reservation-list-create")
        self.staff_user, self.staff_client = make_staff_user()
        self.readonly_user, self.readonly_client = make_readonly_user()
        self.anon_client = APIClient()
        self.apt = make_apartment(code="LC")

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
        self.apt = make_apartment(code="DED")
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
        self.apt = make_apartment(code="BD")

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
        self.apt = make_apartment(code="DS")
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
        self.apt = make_apartment(code="PL")

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
        self.apt = make_apartment(code="BV")

    def test_returns_200(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert response.status_code == status.HTTP_200_OK

    def test_structure_has_apartments_key(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert "apartments" in response.data
        assert "airbnb_monthly" in response.data
        assert "non_airbnb_monthly" in response.data

    def test_revenue_calculation(self):
        make_reservation(
            self.apt,
            created_by=self.staff_user,
            check_in=date(2025, 2, 1),
            check_out=date(2025, 2, 3),
            amount="300.00",
            payment_source="Airbnb",
        )
        response = self.staff_client.get(self.url, {"year": 2025})
        apt_data = response.data["apartments"].get("BV")
        assert apt_data["monthly"][2]["total"] == pytest.approx(300.0)

    def test_unauthenticated_returns_401(self):
        response = self.anon_client.get(self.url, {"year": 2025})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_year_returns_400(self):
        response = self.staff_client.get(self.url, {"year": "bad"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_total_monthly_cost_in_response(self):
        response = self.staff_client.get(self.url, {"year": 2025})
        assert "total_monthly_cost" in response.data
        assert response.data["total_monthly_cost"] == pytest.approx(0.0)

    def test_total_monthly_cost_calculation(self):
        self.apt.monthly_cost = "15500.00"
        self.apt.save()
        apt2 = make_apartment(code="BV2")
        apt2.monthly_cost = "10000.00"
        apt2.save()
        response = self.staff_client.get(self.url, {"year": 2025})
        assert response.data["total_monthly_cost"] == pytest.approx(25500.0)
