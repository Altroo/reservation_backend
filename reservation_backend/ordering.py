"""Allowlisted public column ordering, before pagination or list serialization."""

from decimal import Decimal
from django.db.models import CharField, DecimalField, F, FloatField, TextField, Value
from django.db.models.functions import (
    Cast,
    Coalesce,
    Concat,
    Lower,
    NullIf,
    Round,
    Trim,
)


def direct(names):
    return {name: F(name) for name in names.split()}


def user_name(prefix):
    return Coalesce(
        NullIf(
            Trim(
                Concat(
                    F(f"{prefix}__first_name"), Value(" "), F(f"{prefix}__last_name")
                )
            ),
            Value(""),
        ),
        F(f"{prefix}__email"),
        output_field=CharField(),
    )


def percentage(numerator, denominator, factor=100):
    value = (
        Cast(numerator, FloatField())
        * Value(float(factor))
        / NullIf(Cast(denominator, FloatField()), Value(0.0))
    )
    return Round(Cast(value, DecimalField(max_digits=20, decimal_places=4)), 2)


def fields_for(queryset, field, params):
    model = queryset.model._meta.label_lower
    fields = {
        "accounts.customuser": direct(
            "first_name last_name email gender is_staff is_active date_joined last_login"
        )
    }
    fields.update(
        {
            "building.building": {
                **direct("nom date_created"),
                "created_by_user_name": user_name("created_by_user"),
            },
            "reservation.cost": {
                **direct("description amount date category"),
                "building_nom": F("building__nom"),
                "created_by_user_name": user_name("created_by_user"),
            },
            "reservation.reservation": {
                **direct("guest_name check_in check_out amount payment_source notes"),
                "apartment_nom": F("apartment__nom"),
                "nights": F("check_out") - F("check_in"),
            },
            "local.local": {
                **direct(
                    "nom type_local prix_achat prix_location_mensuel en_location locataire_nom"
                ),
                "building_nom": F("building__nom"),
                "rentabilite": Coalesce(
                    percentage(F("prix_location_mensuel"), F("prix_achat"), 1200),
                    Value(Decimal("0")),
                ),
            },
        }
    )
    return queryset, fields.get(model, {})


def apply_list_ordering(queryset, params):
    ordering = params.get("ordering", "")
    if not ordering or not hasattr(queryset, "model"):
        return queryset
    descending = ordering.startswith("-")
    field = ordering[1:] if descending else ordering
    queryset, fields = fields_for(queryset, field, params)
    expression = fields.get(field)
    if expression is None:
        return queryset
    resolved = expression.resolve_expression(queryset.query)
    if isinstance(resolved.output_field, (CharField, TextField)):
        expression = Lower(expression)
    queryset = queryset.alias(_list_ordering_value=expression)
    order = F("_list_ordering_value")
    return queryset.order_by(
        order.desc(nulls_last=True) if descending else order.asc(nulls_last=True),
        "-pk" if descending else "pk",
    )
