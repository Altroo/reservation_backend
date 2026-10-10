"""Verified native serializers and write views; no model-generated operations."""
from dataclasses import dataclass
from reservation.models import Reservation, Apartment, Cost, HiltonReport
from reservation.serializers import ReservationSerializer, ApartmentSerializer, CostSerializer
from reservation.views import ReservationDetailEditDeleteView, ApartmentDetailView, CostDetailView
from building.models import Building
from building.serializers import BuildingSerializer
from building.views import BuildingDetailView
from local.models import Local, Loyer
from local.serializers import LocalSerializer, LoyerSerializer
from local.views import LocalDetailView, LoyerDetailView
from account.models import CustomUser

@dataclass(frozen=True)
class Resource:
    model: object
    serializer: object = None
    view: object = None
    editable: tuple = ()
    deletable: bool = False

RESOURCES={
 'reservation':Resource(Reservation,ReservationSerializer,ReservationDetailEditDeleteView,('guest_name','notes'),True),
 'building':Resource(Building,BuildingSerializer,BuildingDetailView,('nom',),True),
 'apartment':Resource(Apartment,ApartmentSerializer,ApartmentDetailView,('nom',),True),
 'cost':Resource(Cost,CostSerializer,CostDetailView,('description',),True),
 'local':Resource(Local,LocalSerializer,LocalDetailView,('nom','adresse','locataire_nom','notes'),True),
 'rent':Resource(Loyer,LoyerSerializer,LoyerDetailView,('notes',),True),
 'hilton_report':Resource(HiltonReport),
 'user':Resource(CustomUser),
}
