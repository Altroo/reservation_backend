"""Remove Notification and NotificationPreference from reservation state.

The actual database tables are preserved — they will be adopted by the
``notification`` app in its initial migration (0001).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("reservation", "0011_historicalapartment_historicalcost_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="HistoricalNotification"),
                migrations.DeleteModel(name="HistoricalNotificationPreference"),
                migrations.DeleteModel(name="Notification"),
                migrations.DeleteModel(name="NotificationPreference"),
            ],
            database_operations=[],
        ),
    ]
