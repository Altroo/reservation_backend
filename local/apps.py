from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LocalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "local"
    verbose_name = _("Locaux")
