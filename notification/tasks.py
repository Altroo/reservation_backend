"""Celery tasks for reservation notification reminders."""

import logging
from datetime import datetime, time, timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone
from django.utils.translation import gettext as _

from notification.models import Notification, NotificationPreference
from reservation.models import Reservation

logger = logging.getLogger(__name__)

# Hotel-standard event times
CHECK_IN_TIME = time(15, 0)  # 15:00
CHECK_OUT_TIME = time(12, 0)  # 12:00

# Max lookahead covers the largest reminder (2880 min = 2 days) + 1 day buffer
_MAX_LOOKAHEAD_DAYS = 3


@shared_task(name="notification.check_reservation_reminders")
def check_reservation_reminders():
    """
    Periodic task that checks for upcoming check-in / check-out events
    and creates notifications for users who have configured reminders.
    Runs every minute via Celery Beat.

    Check-in is at 15:00 and check-out is at 12:00.
    Notifications fire ``reminder_minutes`` before those times.
    """
    now = timezone.now()
    today = now.date()
    max_date = today + timedelta(days=_MAX_LOOKAHEAD_DAYS)
    preferences = NotificationPreference.objects.select_related("user").all()
    channel_layer = get_channel_layer()

    for pref in preferences:
        reminder_delta = timedelta(minutes=pref.reminder_minutes)

        if pref.notify_check_in:
            check_in_qs = Reservation.objects.select_related("apartment").filter(
                check_in__gte=today,
                check_in__lte=max_date,
            )
            for res in check_in_qs:
                event_dt = timezone.make_aware(
                    datetime.combine(res.check_in, CHECK_IN_TIME)
                )
                notify_at = event_dt - reminder_delta
                if now >= notify_at:
                    exists = Notification.objects.filter(
                        user=pref.user,
                        reservation=res,
                        notification_type="check_in",
                    ).exists()
                    if not exists:
                        notif = Notification.objects.create(
                            user=pref.user,
                            reservation=res,
                            title=_("Arrivée — %(guest_name)s")
                            % {"guest_name": res.guest_name},
                            message=_(
                                "%(guest_name)s arrive le %(check_in)s à 15h00 "
                                "à l'appartement %(apartment)s."
                            )
                            % {
                                "guest_name": res.guest_name,
                                "check_in": res.check_in,
                                "apartment": res.apartment.nom,
                            },
                            notification_type="check_in",
                        )
                        _broadcast_notification(channel_layer, pref.user.id, notif)

        if pref.notify_check_out:
            check_out_qs = Reservation.objects.select_related("apartment").filter(
                check_out__gte=today,
                check_out__lte=max_date,
            )
            for res in check_out_qs:
                event_dt = timezone.make_aware(
                    datetime.combine(res.check_out, CHECK_OUT_TIME)
                )
                notify_at = event_dt - reminder_delta
                if now >= notify_at:
                    exists = Notification.objects.filter(
                        user=pref.user,
                        reservation=res,
                        notification_type="check_out",
                    ).exists()
                    if not exists:
                        notif = Notification.objects.create(
                            user=pref.user,
                            reservation=res,
                            title=_("Départ — %(guest_name)s")
                            % {"guest_name": res.guest_name},
                            message=_(
                                "%(guest_name)s quitte l'appartement "
                                "%(apartment)s le %(check_out)s à 12h00."
                            )
                            % {
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
