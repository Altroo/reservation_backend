"""Celery tasks for reservation notification reminders."""

import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone
from django.utils.translation import gettext as _

from reservation.models import Notification, NotificationPreference, Reservation

logger = logging.getLogger(__name__)


@shared_task(name="reservation.check_reservation_reminders")
def check_reservation_reminders():
    """
    Periodic task that checks for upcoming check-in / check-out events
    and creates notifications for users who have configured reminders.
    Runs every minute via Celery Beat.
    """
    now = timezone.now()
    today = now.date()
    preferences = NotificationPreference.objects.select_related("user").all()
    channel_layer = get_channel_layer()

    for pref in preferences:
        # For date-based events we compare today's date.
        # If reminder_minutes >= 1440 (1 day), look ahead by that many days.
        # Otherwise, we generate notifications for today's events.
        days_ahead = pref.reminder_minutes // 1440
        target_date = today + timedelta(days=days_ahead)

        reservations = Reservation.objects.select_related("apartment")

        if pref.notify_check_in:
            check_in_qs = reservations.filter(check_in=target_date)
            for res in check_in_qs:
                # Avoid duplicate notifications
                exists = Notification.objects.filter(
                    user=pref.user,
                    reservation=res,
                    notification_type="check_in",
                    date_created__date=today,
                ).exists()
                if not exists:
                    notif = Notification.objects.create(
                        user=pref.user,
                        reservation=res,
                        title=_("Arrivée — %(guest_name)s") % {"guest_name": res.guest_name},
                        message=_(
                            "%(guest_name)s arrive le %(check_in)s "
                            "à l'appartement %(apartment)s."
                        ) % {
                            "guest_name": res.guest_name,
                            "check_in": res.check_in,
                            "apartment": res.apartment.nom,
                        },
                        notification_type="check_in",
                    )
                    _broadcast_notification(channel_layer, pref.user.id, notif)

        if pref.notify_check_out:
            check_out_qs = reservations.filter(check_out=target_date)
            for res in check_out_qs:
                exists = Notification.objects.filter(
                    user=pref.user,
                    reservation=res,
                    notification_type="check_out",
                    date_created__date=today,
                ).exists()
                if not exists:
                    notif = Notification.objects.create(
                        user=pref.user,
                        reservation=res,
                        title=_("Départ — %(guest_name)s") % {"guest_name": res.guest_name},
                        message=_(
                            "%(guest_name)s quitte l'appartement "
                            "%(apartment)s le %(check_out)s."
                        ) % {
                            "guest_name": res.guest_name,
                            "apartment": res.apartment.nom,
                            "check_out": res.check_out,
                        },
                        notification_type="check_out",
                    )
                    _broadcast_notification(channel_layer, pref.user.id, notif)


def _broadcast_notification(channel_layer, user_id, notification):
    """Send a notification event to the user's personal WS group."""
    try:
        async_to_sync(channel_layer.group_send)(
            str(user_id),
            {
                "type": "receive_group_message",
                "message": {
                    "type": "NOTIFICATION",
                    "id": notification.id,
                    "reservation_id": (
                        notification.reservation_id
                        if notification.reservation
                        else None
                    ),
                    "title": notification.title,
                    "message": notification.message,
                    "notification_type": notification.notification_type,
                    "is_read": notification.is_read,
                    "date_created": notification.date_created.isoformat(),
                },
            },
        )
    except Exception:
        logger.exception(
            "Failed to broadcast notification %s to user %s", notification.id, user_id
        )
