from django.db import migrations
from django.db.models import Q


def assign_legacy_apartment_buildings(apps, schema_editor):
    Apartment = apps.get_model("reservation", "Apartment")
    Building = apps.get_model("building", "Building")

    hilton = Building.objects.filter(nom__iexact="Hilton residence").first()
    if hilton:
        Apartment.objects.filter(building__isnull=True).filter(
            Q(nom__istartswith="HR ")
            | Q(nom__istartswith="HR étage")
            | Q(nom__iexact="City Center 5B")
        ).update(building=hilton)

    nectar = Building.objects.filter(nom__iexact="Nectar").first()
    if nectar:
        Apartment.objects.filter(
            building__isnull=True,
            nom__istartswith="NR ",
        ).update(building=nectar)


class Migration(migrations.Migration):
    dependencies = [
        ("building", "0001_initial"),
        ("reservation", "0018_historicalcostcategoryoption_historicalhiltonreport_and_more"),
    ]

    operations = [
        migrations.RunPython(
            assign_legacy_apartment_buildings,
            migrations.RunPython.noop,
        ),
    ]
