import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from account.models import CustomUser
from building.models import Building

pytestmark = pytest.mark.django_db


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_staff_user(email="staff-bldg@test.com", password="securepass123"):
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


def make_readonly_user(email="readonly-bldg@test.com", password="securepass123"):
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


def make_building(nom="Hilton Résidence", **kwargs):
    return Building.objects.create(nom=nom, **kwargs)


# ── Model Tests ───────────────────────────────────────────────────────────────


class TestBuildingModel:
    def test_str(self):
        b = Building(nom="Hilton Résidence")
        assert str(b) == "Hilton Résidence"

    def test_unique_nom(self):
        from django.db import IntegrityError

        make_building(nom="UNQ")
        with pytest.raises(IntegrityError):
            make_building(nom="UNQ")

    def test_default_ordering(self):
        make_building(nom="ZZZ")
        make_building(nom="AAA")
        names = list(Building.objects.values_list("nom", flat=True))
        assert names == ["AAA", "ZZZ"]


# ── List + Create View Tests ─────────────────────────────────────────────────


class TestBuildingListCreateView:
    def setup_method(self):
        self.url = reverse("building:building-list-create")
        self.staff_user, self.staff_client = make_staff_user()

    def test_list_empty(self):
        resp = self.staff_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []

    def test_list_with_data(self):
        make_building(nom="B1")
        make_building(nom="B2")
        resp = self.staff_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 2

    def test_list_ordered_by_nom(self):
        make_building(nom="Zeta")
        make_building(nom="Alpha")
        resp = self.staff_client.get(self.url)
        assert resp.data[0]["nom"] == "Alpha"
        assert resp.data[1]["nom"] == "Zeta"

    def test_create_success(self):
        resp = self.staff_client.post(self.url, {"nom": "New Résidence"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["nom"] == "New Résidence"
        assert resp.data["created_by_user"] == self.staff_user.pk

    def test_create_permission_denied(self):
        _, ro_client = make_readonly_user()
        resp = ro_client.post(self.url, {"nom": "Blocked"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_nom(self):
        make_building(nom="DUP")
        resp = self.staff_client.post(self.url, {"nom": "DUP"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_blank_nom(self):
        resp = self.staff_client.post(self.url, {"nom": ""})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated(self):
        client = APIClient()
        resp = client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ── Detail View Tests ─────────────────────────────────────────────────────────


class TestBuildingDetailView:
    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(
            email="detailstaff-bldg@test.com"
        )

    def test_get(self):
        b = make_building(nom="DET")
        url = reverse("building:building-detail", args=[b.pk])
        resp = self.staff_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["nom"] == "DET"

    def test_get_not_found(self):
        url = reverse("building:building-detail", args=[99999])
        resp = self.staff_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_put(self):
        b = make_building(nom="OLD")
        url = reverse("building:building-detail", args=[b.pk])
        resp = self.staff_client.put(url, {"nom": "NEW"})
        assert resp.status_code == status.HTTP_200_OK
        b.refresh_from_db()
        assert b.nom == "NEW"

    def test_put_permission_denied(self):
        _, ro_client = make_readonly_user(email="roupd-bldg@test.com")
        b = make_building(nom="NOUP")
        url = reverse("building:building-detail", args=[b.pk])
        resp = ro_client.put(url, {"nom": "X"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_put_duplicate_nom(self):
        make_building(nom="EXISTING")
        b = make_building(nom="OTHER")
        url = reverse("building:building-detail", args=[b.pk])
        resp = self.staff_client.put(url, {"nom": "EXISTING"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete(self):
        b = make_building(nom="DEL")
        url = reverse("building:building-detail", args=[b.pk])
        resp = self.staff_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Building.objects.filter(pk=b.pk).exists()

    def test_delete_with_apartments_blocked(self):
        from reservation.models import Apartment

        b = make_building(nom="DELAPT")
        Apartment.objects.create(nom="APT1", building=b)
        url = reverse("building:building-detail", args=[b.pk])
        resp = self.staff_client.delete(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_with_locaux_blocked(self):
        from local.models import Local

        b = make_building(nom="DELLOC")
        Local.objects.create(
            nom="LOC1",
            building=b,
            type_local="Bureau",
            prix_achat="100000.00",
            prix_location_mensuel="5000.00",
        )
        url = reverse("building:building-detail", args=[b.pk])
        resp = self.staff_client.delete(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_permission_denied(self):
        _, ro_client = make_readonly_user(email="rodel-bldg@test.com")
        b = make_building(nom="NODEL")
        url = reverse("building:building-detail", args=[b.pk])
        resp = ro_client.delete(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── Bulk Delete Tests ─────────────────────────────────────────────────────────


class TestBulkDeleteBuildingView:
    def setup_method(self):
        self.url = reverse("building:building-bulk-delete")
        self.staff_user, self.staff_client = make_staff_user(
            email="bulkstaff-bldg@test.com"
        )

    def test_bulk_delete(self):
        b1 = make_building(nom="BD1")
        b2 = make_building(nom="BD2")
        resp = self.staff_client.delete(
            self.url, {"ids": [b1.pk, b2.pk]}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert Building.objects.count() == 0

    def test_bulk_delete_skips_with_apartments(self):
        from reservation.models import Apartment

        b1 = make_building(nom="BDA1")
        Apartment.objects.create(nom="APT-BD", building=b1)
        b2 = make_building(nom="BDA2")
        resp = self.staff_client.delete(
            self.url, {"ids": [b1.pk, b2.pk]}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert Building.objects.filter(pk=b1.pk).exists()
        assert not Building.objects.filter(pk=b2.pk).exists()

    def test_bulk_delete_skips_with_locaux(self):
        from local.models import Local

        b1 = make_building(nom="BDL1")
        Local.objects.create(
            nom="LOC-BD",
            building=b1,
            type_local="Bureau",
            prix_achat="100000.00",
            prix_location_mensuel="5000.00",
        )
        b2 = make_building(nom="BDL2")
        resp = self.staff_client.delete(
            self.url, {"ids": [b1.pk, b2.pk]}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert Building.objects.filter(pk=b1.pk).exists()
        assert not Building.objects.filter(pk=b2.pk).exists()

    def test_bulk_delete_permission_denied(self):
        _, ro_client = make_readonly_user(email="robulk-bldg@test.com")
        resp = ro_client.delete(self.url, {"ids": [1]}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_delete_empty_ids(self):
        resp = self.staff_client.delete(self.url, {"ids": []}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_delete_missing_ids(self):
        resp = self.staff_client.delete(self.url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── Building filter integration tests ─────────────────────────────────────────


class TestBuildingFilterOnReservationPlanning:
    """Test that the reservation planning view filters by building."""

    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(
            email="planstaff-bldg@test.com"
        )

    def test_planning_filter_by_building(self):
        from reservation.models import Apartment, Reservation

        b1 = make_building(nom="Hilton")
        b2 = make_building(nom="Nectar")
        apt1 = Apartment.objects.create(nom="H-101", building=b1)
        apt2 = Apartment.objects.create(nom="N-201", building=b2)
        Reservation.objects.create(
            apartment=apt1,
            guest_name="Guest1",
            check_in="2026-03-01",
            check_out="2026-03-05",
            amount="1000.00",
            created_by_user=self.staff_user,
        )
        Reservation.objects.create(
            apartment=apt2,
            guest_name="Guest2",
            check_in="2026-03-10",
            check_out="2026-03-15",
            amount="2000.00",
            created_by_user=self.staff_user,
        )

        url = reverse("reservation:planning-month")
        resp = self.staff_client.get(url, {"year": 2026, "month": 3, "building": b1.pk})
        assert resp.status_code == status.HTTP_200_OK
        assert "H-101" in resp.data["apartments"]
        assert "N-201" not in resp.data["apartments"]

    def test_planning_no_filter_returns_all(self):
        from reservation.models import Apartment

        b1 = make_building(nom="Hilton-NF")
        Apartment.objects.create(nom="H-NF", building=b1)
        Apartment.objects.create(nom="NoBuilding")

        url = reverse("reservation:planning-month")
        resp = self.staff_client.get(url, {"year": 2026, "month": 3})
        assert len(resp.data["apartments"]) == 2


class TestBuildingFilterOnDashboard:
    """Test that the reservation dashboard filters by building."""

    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(
            email="dashstaff-bldg@test.com"
        )

    def test_dashboard_filter_by_building(self):
        from reservation.models import Apartment, Reservation

        b1 = make_building(nom="Hilton-D")
        apt1 = Apartment.objects.create(nom="HD-101", building=b1)
        apt2 = Apartment.objects.create(nom="Other-201")
        Reservation.objects.create(
            apartment=apt1,
            guest_name="G1",
            check_in="2026-03-01",
            check_out="2026-03-05",
            amount="1000.00",
            created_by_user=self.staff_user,
        )
        Reservation.objects.create(
            apartment=apt2,
            guest_name="G2",
            check_in="2026-03-10",
            check_out="2026-03-15",
            amount="2000.00",
            created_by_user=self.staff_user,
        )

        url = reverse("reservation:dashboard-stats")
        resp = self.staff_client.get(url, {"year": 2026, "building": b1.pk})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_revenue"] == 1000.0


class TestBuildingFilterOnLocalPlanning:
    """Test that the local planning view filters by building."""

    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(
            email="locplanstaff-bldg@test.com"
        )

    def test_local_planning_filter_by_building(self):
        from local.models import Local

        b1 = make_building(nom="Hilton-LP")
        b2 = make_building(nom="Nectar-LP")
        Local.objects.create(
            nom="L1",
            building=b1,
            type_local="Bureau",
            prix_achat="100000.00",
            prix_location_mensuel="5000.00",
        )
        Local.objects.create(
            nom="L2",
            building=b2,
            type_local="Magasin",
            prix_achat="200000.00",
            prix_location_mensuel="8000.00",
        )

        url = reverse("local:local-planning")
        resp = self.staff_client.get(url, {"year": 2026, "building": b1.pk})
        assert resp.status_code == status.HTTP_200_OK
        noms = [loc["nom"] for loc in resp.data["locaux"]]
        assert "L1" in noms
        assert "L2" not in noms


class TestBuildingFilterOnLocalDashboard:
    """Test that the local dashboard filters by building."""

    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(
            email="locdashstaff-bldg@test.com"
        )

    def test_local_dashboard_filter_by_building(self):
        from local.models import Local

        b1 = make_building(nom="Hilton-LD")
        Local.objects.create(
            nom="LD1",
            building=b1,
            type_local="Bureau",
            prix_achat="100000.00",
            prix_location_mensuel="5000.00",
        )
        Local.objects.create(
            nom="LD2",
            type_local="Magasin",
            prix_achat="200000.00",
            prix_location_mensuel="8000.00",
        )

        url = reverse("local:local-dashboard")
        resp = self.staff_client.get(url, {"year": 2026, "building": b1.pk})
        assert resp.status_code == status.HTTP_200_OK
        noms = [loc["nom"] for loc in resp.data["locaux"]]
        assert "LD1" in noms
        assert "LD2" not in noms


class TestApartmentBuildingField:
    """Test that apartment serializer includes building fields."""

    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(email="aptbldg@test.com")

    def test_apartment_with_building(self):
        from reservation.models import Apartment

        b = make_building(nom="APT-BLDG")
        Apartment.objects.create(nom="A1", building=b)
        url = reverse("reservation:apartment-list")
        resp = self.staff_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        apt = resp.data[0]
        assert apt["building"] == b.pk
        assert apt["building_nom"] == "APT-BLDG"

    def test_apartment_without_building(self):
        from reservation.models import Apartment

        Apartment.objects.create(nom="A2")
        url = reverse("reservation:apartment-list")
        resp = self.staff_client.get(url)
        apt = resp.data[0]
        assert apt["building"] is None
        assert apt["building_nom"] is None


class TestLocalBuildingField:
    """Test that local serializer includes building fields."""

    def setup_method(self):
        self.staff_user, self.staff_client = make_staff_user(email="locbldg@test.com")

    def test_local_with_building(self):
        from local.models import Local

        b = make_building(nom="LOC-BLDG")
        Local.objects.create(
            nom="LB1",
            building=b,
            type_local="Bureau",
            prix_achat="100000.00",
            prix_location_mensuel="5000.00",
        )
        url = reverse("local:local-list-create")
        resp = self.staff_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        loc = resp.data[0]
        assert loc["building"] == b.pk
        assert loc["building_nom"] == "LOC-BLDG"

    def test_local_without_building(self):
        from local.models import Local

        Local.objects.create(
            nom="LB2",
            type_local="Bureau",
            prix_achat="100000.00",
            prix_location_mensuel="5000.00",
        )
        url = reverse("local:local-list-create")
        resp = self.staff_client.get(url)
        loc = resp.data[0]
        assert loc["building"] is None
        assert loc["building_nom"] is None
