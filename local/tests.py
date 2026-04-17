from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from account.models import CustomUser
from local.models import Local, Loyer

pytestmark = pytest.mark.django_db


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_staff_user(email="staff-local@test.com", password="securepass123"):
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


def make_readonly_user(email="readonly-local@test.com", password="securepass123"):
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


def make_local(nom="Bureau A", **kwargs):
    defaults = {
        "type_local": "Bureau",
        "prix_achat": "1000000.00",
        "prix_location_mensuel": "5000.00",
        "en_location": False,
    }
    defaults.update(kwargs)
    return Local.objects.create(nom=nom, **defaults)


def make_loyer(local, mois=1, annee=2026, **kwargs):
    defaults = {
        "montant": "5000.00",
        "paye": False,
    }
    defaults.update(kwargs)
    return Loyer.objects.create(local=local, mois=mois, annee=annee, **defaults)


# ── Model Tests ───────────────────────────────────────────────────────────────


class TestLocalModel:
    def test_str(self):
        local = Local(nom="Bureau A", type_local="Bureau")
        assert str(local) == "Bureau A (Bureau)"

    def test_str_magasin(self):
        local = Local(nom="Shop 1", type_local="Magasin")
        assert str(local) == "Shop 1 (Magasin)"

    def test_unique_nom(self):
        from django.db import IntegrityError

        make_local(nom="UNQ")
        with pytest.raises(IntegrityError):
            make_local(nom="UNQ")

    def test_rentabilite(self):
        local = make_local(
            nom="R1",
            prix_achat="1000000.00",
            prix_location_mensuel="5000.00",
        )
        # (5000 * 12) / 1000000 * 100 = 6.00
        assert local.rentabilite == Decimal("6.00")

    def test_rentabilite_zero_achat(self):
        local = make_local(
            nom="R0",
            prix_achat="0.00",
            prix_location_mensuel="5000.00",
        )
        assert local.rentabilite == Decimal("0.00")

    def test_default_ordering(self):
        make_local(nom="ZZZ")
        make_local(nom="AAA")
        names = list(Local.objects.values_list("nom", flat=True))
        assert names == ["AAA", "ZZZ"]


class TestLoyerModel:
    def test_str(self):
        local = make_local(nom="L1")
        loyer = Loyer(
            local=local,
            mois=3,
            annee=2026,
            montant=Decimal("5000.00"),
        )
        assert "L1" in str(loyer)
        assert "03/2026" in str(loyer)

    def test_unique_constraint(self):
        from django.db import IntegrityError

        local = make_local(nom="UC")
        make_loyer(local, mois=1, annee=2026)
        with pytest.raises(IntegrityError):
            make_loyer(local, mois=1, annee=2026)

    def test_ordering(self):
        local = make_local(nom="ORD")
        make_loyer(local, mois=1, annee=2025)
        make_loyer(local, mois=6, annee=2026)
        make_loyer(local, mois=3, annee=2026)
        loyers = list(Loyer.objects.filter(local=local).values_list("annee", "mois"))
        assert loyers == [(2026, 6), (2026, 3), (2025, 1)]


# ── Local API Tests ───────────────────────────────────────────────────────────


class TestLocalListCreateView:
    def setup_method(self):
        self.url = reverse("local:local-list-create")
        self.staff_user, self.staff_client = make_staff_user()

    def test_list_empty(self):
        resp = self.staff_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []

    def test_list_with_data(self):
        make_local(nom="B1")
        make_local(nom="B2")
        resp = self.staff_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 2

    def test_list_paginated(self):
        make_local(nom="P1")
        resp = self.staff_client.get(self.url, {"pagination": "true"})
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.data
        assert "count" in resp.data

    def test_list_filter_type(self):
        make_local(nom="B1", type_local="Bureau")
        make_local(nom="M1", type_local="Magasin")
        resp = self.staff_client.get(self.url, {"type_local": "Bureau"})
        assert len(resp.data) == 1
        assert resp.data[0]["nom"] == "B1"

    def test_list_filter_en_location(self):
        make_local(nom="OCC", en_location=True)
        make_local(nom="FREE", en_location=False)
        resp = self.staff_client.get(self.url, {"en_location": "true"})
        assert len(resp.data) == 1
        assert resp.data[0]["nom"] == "OCC"

    def test_list_search(self):
        make_local(nom="Alpha Bureau")
        make_local(nom="Beta Magasin")
        resp = self.staff_client.get(self.url, {"search": "Alpha"})
        assert len(resp.data) == 1

    def test_create_success(self):
        data = {
            "nom": "New Local",
            "type_local": "Bureau",
            "prix_achat": "500000.00",
            "prix_location_mensuel": "3000.00",
        }
        resp = self.staff_client.post(self.url, data)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["nom"] == "New Local"
        assert resp.data["rentabilite"] is not None

    def test_create_permission_denied(self):
        _, ro_client = make_readonly_user()
        data = {
            "nom": "Blocked",
            "type_local": "Bureau",
            "prix_achat": "500000.00",
            "prix_location_mensuel": "3000.00",
        }
        resp = ro_client.post(self.url, data)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_nom(self):
        make_local(nom="DUP")
        data = {
            "nom": "DUP",
            "type_local": "Bureau",
            "prix_achat": "500000.00",
            "prix_location_mensuel": "3000.00",
        }
        resp = self.staff_client.post(self.url, data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated(self):
        client = APIClient()
        resp = client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestLocalDetailView:
    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(
            email="detailstaff@test.com"
        )

    def test_get(self):
        local = make_local(nom="DET")
        url = reverse("local:local-detail", args=[local.pk])
        resp = self.staff_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["nom"] == "DET"

    def test_get_not_found(self):
        url = reverse("local:local-detail", args=[99999])
        resp = self.staff_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_put(self):
        local = make_local(nom="UPD")
        url = reverse("local:local-detail", args=[local.pk])
        data = {
            "nom": "Updated",
            "type_local": "Magasin",
            "prix_achat": "800000.00",
            "prix_location_mensuel": "4000.00",
        }
        resp = self.staff_client.put(url, data)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["nom"] == "Updated"

    def test_put_permission_denied(self):
        _, ro_client = make_readonly_user(email="roupd@test.com")
        local = make_local(nom="NOUP")
        url = reverse("local:local-detail", args=[local.pk])
        resp = ro_client.put(url, {"nom": "X"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete(self):
        local = make_local(nom="DEL")
        url = reverse("local:local-detail", args=[local.pk])
        resp = self.staff_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Local.objects.filter(pk=local.pk).exists()

    def test_delete_with_loyers_blocked(self):
        local = make_local(nom="DELLOY")
        make_loyer(local, mois=1, annee=2026)
        url = reverse("local:local-detail", args=[local.pk])
        resp = self.staff_client.delete(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_permission_denied(self):
        _, ro_client = make_readonly_user(email="rodel@test.com")
        local = make_local(nom="NODEL")
        url = reverse("local:local-detail", args=[local.pk])
        resp = ro_client.delete(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestBulkDeleteLocalView:
    def setup_method(self):
        self.url = reverse("local:local-bulk-delete")
        self.staff_user, self.staff_client = make_staff_user(email="bulkstaff@test.com")

    def test_bulk_delete(self):
        l1 = make_local(nom="BD1")
        l2 = make_local(nom="BD2")
        resp = self.staff_client.delete(
            self.url, {"ids": [l1.pk, l2.pk]}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert Local.objects.count() == 0

    def test_bulk_delete_skips_with_loyers(self):
        l1 = make_local(nom="BDL1")
        make_loyer(l1, mois=1, annee=2026)
        l2 = make_local(nom="BDL2")
        resp = self.staff_client.delete(
            self.url, {"ids": [l1.pk, l2.pk]}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        # l1 should remain (has loyer), l2 deleted
        assert Local.objects.filter(pk=l1.pk).exists()
        assert not Local.objects.filter(pk=l2.pk).exists()

    def test_bulk_delete_permission_denied(self):
        _, ro_client = make_readonly_user(email="robulk@test.com")
        resp = ro_client.delete(self.url, {"ids": [1]}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── Loyer API Tests ───────────────────────────────────────────────────────────


class TestLoyerListCreateView:
    def setup_method(self):
        self.url = reverse("local:loyer-list-create")
        self.staff_user, self.staff_client = make_staff_user(
            email="loyerstaff@test.com"
        )

    def test_list_empty(self):
        resp = self.staff_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []

    def test_list_with_data(self):
        local = make_local(nom="LL1")
        make_loyer(local, mois=1, annee=2026)
        make_loyer(local, mois=2, annee=2026)
        resp = self.staff_client.get(self.url)
        assert len(resp.data) == 2

    def test_list_filter_by_local(self):
        l1 = make_local(nom="FL1")
        l2 = make_local(nom="FL2")
        make_loyer(l1, mois=1, annee=2026)
        make_loyer(l2, mois=1, annee=2026)
        resp = self.staff_client.get(self.url, {"local": l1.pk})
        assert len(resp.data) == 1

    def test_list_filter_by_year(self):
        local = make_local(nom="FY")
        make_loyer(local, mois=1, annee=2025)
        make_loyer(local, mois=1, annee=2026)
        resp = self.staff_client.get(self.url, {"annee": 2026})
        assert len(resp.data) == 1

    def test_list_filter_paye(self):
        local = make_local(nom="FP")
        make_loyer(local, mois=1, annee=2026, paye=True)
        make_loyer(local, mois=2, annee=2026, paye=False)
        resp = self.staff_client.get(self.url, {"paye": "true"})
        assert len(resp.data) == 1

    def test_create_success(self):
        local = make_local(nom="CL")
        data = {
            "local": local.pk,
            "mois": 3,
            "annee": 2026,
            "montant": "5000.00",
        }
        resp = self.staff_client.post(self.url, data)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["local_nom"] == "CL"

    def test_create_invalid_month(self):
        local = make_local(nom="IM")
        data = {
            "local": local.pk,
            "mois": 13,
            "annee": 2026,
            "montant": "5000.00",
        }
        resp = self.staff_client.post(self.url, data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_duplicate(self):
        local = make_local(nom="DL")
        make_loyer(local, mois=1, annee=2026)
        data = {
            "local": local.pk,
            "mois": 1,
            "annee": 2026,
            "montant": "5000.00",
        }
        resp = self.staff_client.post(self.url, data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_permission_denied(self):
        _, ro_client = make_readonly_user(email="roloyer@test.com")
        local = make_local(nom="PD")
        data = {
            "local": local.pk,
            "mois": 1,
            "annee": 2026,
            "montant": "5000.00",
        }
        resp = ro_client.post(self.url, data)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestLoyerDetailView:
    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(
            email="loyerdetail@test.com"
        )

    def test_get(self):
        local = make_local(nom="LD")
        loyer = make_loyer(local, mois=1, annee=2026)
        url = reverse("local:loyer-detail", args=[loyer.pk])
        resp = self.staff_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_put(self):
        local = make_local(nom="LU")
        loyer = make_loyer(local, mois=1, annee=2026)
        url = reverse("local:loyer-detail", args=[loyer.pk])
        data = {
            "local": local.pk,
            "mois": 1,
            "annee": 2026,
            "montant": "6000.00",
            "paye": True,
            "date_paiement": "2026-01-15",
        }
        resp = self.staff_client.put(url, data)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["montant"] == "6000.00"

    def test_delete(self):
        local = make_local(nom="LDL")
        loyer = make_loyer(local, mois=1, annee=2026)
        url = reverse("local:loyer-detail", args=[loyer.pk])
        resp = self.staff_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT


class TestLoyerTogglePaidView:
    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(email="toggle@test.com")

    def test_toggle_to_paid(self):
        local = make_local(nom="TP")
        loyer = make_loyer(local, mois=1, annee=2026, paye=False)
        url = reverse("local:loyer-toggle-paid", args=[loyer.pk])
        resp = self.staff_client.patch(url, {"paye": True}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["paye"] is True

    def test_toggle_to_unpaid(self):
        local = make_local(nom="TU")
        loyer = make_loyer(
            local,
            mois=1,
            annee=2026,
            paye=True,
            date_paiement=date(2026, 1, 15),
        )
        url = reverse("local:loyer-toggle-paid", args=[loyer.pk])
        resp = self.staff_client.patch(url, {"paye": False}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["paye"] is False

    def test_toggle_missing_field(self):
        local = make_local(nom="TM")
        loyer = make_loyer(local, mois=1, annee=2026)
        url = reverse("local:loyer-toggle-paid", args=[loyer.pk])
        resp = self.staff_client.patch(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_toggle_permission_denied(self):
        _, ro_client = make_readonly_user(email="rotoggle@test.com")
        local = make_local(nom="TPN")
        loyer = make_loyer(local, mois=1, annee=2026)
        url = reverse("local:loyer-toggle-paid", args=[loyer.pk])
        resp = ro_client.patch(url, {"paye": True}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── Planning API Tests ────────────────────────────────────────────────────────


class TestLocalPlanningView:
    def setup_method(self):
        self.url = reverse("local:local-planning")
        self.staff_user, self.staff_client = make_staff_user(email="planning@test.com")

    @staticmethod
    def _freeze_today(monkeypatch, frozen_date: date):
        class FrozenDate(date):
            @classmethod
            def today(cls):
                return frozen_date

        monkeypatch.setattr("local.views.date", FrozenDate)

    def test_planning_empty(self):
        resp = self.staff_client.get(self.url, {"year": 2026})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["year"] == 2026
        assert resp.data["locaux"] == []

    def test_planning_with_data(self):
        local = make_local(nom="PL1", en_location=True)
        make_loyer(local, mois=1, annee=2026, paye=True)
        make_loyer(local, mois=2, annee=2026, paye=False)
        resp = self.staff_client.get(self.url, {"year": 2026})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["locaux"]) == 1
        loc = resp.data["locaux"][0]
        assert loc["months"][1]["paye"] is True
        assert loc["months"][2]["paye"] is False
        assert loc["months"][3] is None

    def test_planning_invalid_year(self):
        resp = self.staff_client.get(self.url, {"year": "abc"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_planning_adds_current_month_implicit_unpaid_rent(self, monkeypatch):
        self._freeze_today(monkeypatch, date(2026, 4, 17))
        local = make_local(nom="PL2", en_location=True, prix_location_mensuel="6500.00")
        make_loyer(local, mois=3, annee=2026, paye=True, montant="6500.00")

        resp = self.staff_client.get(self.url, {"year": 2026})
        assert resp.status_code == status.HTTP_200_OK

        loc = resp.data["locaux"][0]
        assert loc["months"][4]["id"] is None
        assert loc["months"][4]["paye"] is False
        assert loc["months"][4]["is_implicit"] is True
        assert loc["months"][4]["montant"] == "6500.00"


# ── Dashboard API Tests ───────────────────────────────────────────────────────


class TestLocalDashboardView:
    def setup_method(self):
        self.url = reverse("local:local-dashboard")
        self.staff_user, self.staff_client = make_staff_user(email="dashboard@test.com")

    def test_dashboard_empty(self):
        resp = self.staff_client.get(self.url, {"year": 2026})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_benefice_ht"] == "0.00"
        assert resp.data["total_en_location"] == 0
        assert resp.data["total_libres"] == 0

    def test_dashboard_with_data(self, monkeypatch):
        TestLocalPlanningView._freeze_today(monkeypatch, date(2026, 4, 17))
        l1 = make_local(
            nom="DB1",
            en_location=True,
            prix_achat="1000000.00",
            prix_location_mensuel="5000.00",
        )
        l2 = make_local(
            nom="DB2",
            en_location=False,
            prix_achat="2000000.00",
            prix_location_mensuel="8000.00",
        )
        make_loyer(l1, mois=1, annee=2026, paye=True, montant="5000.00")
        make_loyer(l1, mois=2, annee=2026, paye=True, montant="5000.00")
        make_loyer(l1, mois=3, annee=2026, paye=False, montant="5000.00")

        resp = self.staff_client.get(self.url, {"year": 2026})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_benefice_ht"] == "10000.00"
        assert resp.data["total_en_location"] == 1
        assert resp.data["total_libres"] == 1
        assert len(resp.data["locaux"]) == 2

        db1 = next(l for l in resp.data["locaux"] if l["nom"] == "DB1")
        assert db1["rentabilite"] == "6.00"
        assert db1["loyers_payes"] == "10000.00"
        assert db1["loyers_impayes"] == "10000.00"

    def test_dashboard_invalid_year(self):
        resp = self.staff_client.get(self.url, {"year": "xyz"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── Years API Tests ───────────────────────────────────────────────────────────


class TestLocalYearsView:
    def setup_method(self):
        self.url = reverse("local:local-years")
        self.staff_user, self.staff_client = make_staff_user(email="years@test.com")

    def test_years_empty(self):
        resp = self.staff_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["years"] == []

    def test_years_with_data(self):
        local = make_local(nom="YR")
        make_loyer(local, mois=1, annee=2025)
        make_loyer(local, mois=1, annee=2026)
        resp = self.staff_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["years"] == [2026, 2025]
