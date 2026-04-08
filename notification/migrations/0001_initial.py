"""Adopt Notification and NotificationPreference tables from reservation app.

The tables ``reservation_notificationpreference`` and ``reservation_notification``
already exist in the database.  This migration creates the Django state for the
``notification`` app so it owns those models.  No DDL is emitted.
"""

import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("reservation", "0012_remove_notification_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── NotificationPreference ──────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="NotificationPreference",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "notify_check_in",
                            models.BooleanField(
                                default=True,
                                verbose_name="Notifier à l'arrivée",
                            ),
                        ),
                        (
                            "notify_check_out",
                            models.BooleanField(
                                default=True,
                                verbose_name="Notifier au départ",
                            ),
                        ),
                        (
                            "reminder_minutes",
                            models.IntegerField(
                                choices=[
                                    (0, "Au moment de l'événement"),
                                    (15, "15 minutes avant"),
                                    (30, "30 minutes avant"),
                                    (60, "1 heure avant"),
                                    (120, "2 heures avant"),
                                    (1440, "1 jour avant"),
                                    (2880, "2 jours avant"),
                                ],
                                default=60,
                                verbose_name="Rappel avant (minutes)",
                            ),
                        ),
                        (
                            "date_created",
                            models.DateTimeField(
                                auto_now_add=True,
                                verbose_name="Date création",
                            ),
                        ),
                        (
                            "date_updated",
                            models.DateTimeField(
                                auto_now=True,
                                verbose_name="Date modification",
                            ),
                        ),
                        (
                            "user",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="notification_preference",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="Utilisateur",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Préférence de notification",
                        "verbose_name_plural": "Préférences de notification",
                        "db_table": "reservation_notificationpreference",
                    },
                ),
            ],
            database_operations=[],
        ),
        # ── Notification ────────────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Notification",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "title",
                            models.CharField(
                                max_length=255,
                                verbose_name="Titre",
                            ),
                        ),
                        (
                            "message",
                            models.TextField(verbose_name="Message"),
                        ),
                        (
                            "notification_type",
                            models.CharField(
                                choices=[
                                    ("check_in", "Arrivée"),
                                    ("check_out", "Départ"),
                                ],
                                max_length=20,
                                verbose_name="Type",
                            ),
                        ),
                        (
                            "is_read",
                            models.BooleanField(
                                default=False,
                                verbose_name="Lu",
                            ),
                        ),
                        (
                            "date_created",
                            models.DateTimeField(
                                auto_now_add=True,
                                db_index=True,
                                verbose_name="Date création",
                            ),
                        ),
                        (
                            "reservation",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="notifications",
                                to="reservation.reservation",
                                verbose_name="Réservation",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="notifications",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="Utilisateur",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Notification",
                        "verbose_name_plural": "Notifications",
                        "ordering": ("-date_created",),
                        "db_table": "reservation_notification",
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
