from io import BytesIO
from os import path
from uuid import uuid4

from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from reservation_backend.settings import API_URL
from .managers import CustomUserManager


def get_avatar_path(_, filename):
    _, ext = path.splitext(filename)
    return path.join("user_avatars/", str(uuid4()) + ext)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        "Adresse e‑mail", unique=True, help_text="Adresse e‑mail de l'utilisateur"
    )
    first_name = models.CharField(
        "Prénom", max_length=30, blank=True, help_text="Prénom de l'utilisateur"
    )
    last_name = models.CharField(
        "Nom", max_length=30, blank=True, help_text="Nom de famille de l'utilisateur"
    )
    GENDER_CHOICES = (("", "Unset"), ("H", "Homme"), ("F", "Femme"))
    gender = models.CharField(
        verbose_name="Sexe",
        max_length=1,
        choices=GENDER_CHOICES,
        default="",
        help_text="Sexe de l'utilisateur",
    )
    avatar = models.ImageField(
        verbose_name="Photo de profil",
        upload_to=get_avatar_path,
        blank=True,
        null=True,
        default=None,
        help_text="Image de profil de l'utilisateur",
    )
    avatar_cropped = models.ImageField(
        upload_to=get_avatar_path,
        blank=True,
        null=True,
        default=None,
        verbose_name="Photo de profil recadrée",
        max_length=1000,
        help_text="Version recadrée de la photo de profil",
    )
    is_staff = models.BooleanField(
        "Statut personnel",
        default=False,
        db_index=True,
        help_text="Indique si l'utilisateur peut se connecter au panneau d'administration.",
    )
    is_active = models.BooleanField(
        "Actif",
        default=True,
        db_index=True,
        help_text="Indique si ce compte doit être considéré comme actif.",
    )
    date_joined = models.DateTimeField(
        "Date d'inscription",
        default=timezone.now,
        db_index=True,
        help_text="Horodatage de l'inscription de l'utilisateur.",
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification",
        db_index=True,
        help_text="Horodatage de la dernière modification du profil.",
    )
    password_reset_code = models.CharField(
        verbose_name="Mot de passe - Code de réinitialisation",
        blank=True,
        null=True,
        db_index=True,
        help_text="Code de réinitialisation du mot de passe (généré automatiquement).",
    )
    password_reset_code_created_at = models.DateTimeField(
        verbose_name="Mot de passe - Date de création du code",
        blank=True,
        null=True,
        db_index=True,
        help_text="Date à laquelle le code de réinitialisation a été créé.",
    )
    task_id_password_reset = models.CharField(
        verbose_name="Mot de passe - Task ID de réinitialisation",
        max_length=40,
        default=None,
        null=True,
        blank=True,
        db_index=True,
        help_text="Identifiant de la tâche Celery de réinitialisation du mot de passe.",
    )
    default_password_set = models.BooleanField(
        verbose_name="Mot de passe par défaut défini",
        default=False,
        db_index=True,
        help_text="Indique si le mot de passe par défaut a été défini.",
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    history = HistoricalRecords(
        verbose_name="Historique Utilisateur",
        verbose_name_plural="Historiques Utilisateurs",
    )

    def __str__(self):
        full_name = "{} {}".format(self.first_name, self.last_name).strip()
        return full_name if full_name else self.email

    @property
    def get_absolute_avatar_img(self):
        if self.avatar:
            return f"{API_URL}{self.avatar.url}"
        return None

    @property
    def get_absolute_avatar_cropped_img(self):
        if self.avatar_cropped:
            return f"{API_URL}{self.avatar_cropped.url}"
        return None

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ("-date_joined",)

    def save_image(self, file_name, image):
        if not isinstance(image, BytesIO):
            return
        getattr(self, file_name).save(
            f"{str(uuid4())}.webp", ContentFile(image.getvalue()), save=True
        )
