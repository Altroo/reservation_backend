from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notification", "0002_historicalnotification_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalnotificationpreference",
            name="channel_email",
            field=models.BooleanField(default=True, verbose_name="Canal email"),
        ),
        migrations.AddField(
            model_name="historicalnotificationpreference",
            name="channel_push",
            field=models.BooleanField(default=True, verbose_name="Canal push"),
        ),
        migrations.AddField(
            model_name="historicalnotificationpreference",
            name="channel_sms",
            field=models.BooleanField(default=False, verbose_name="Canal SMS"),
        ),
        migrations.AddField(
            model_name="historicalnotificationpreference",
            name="notify_unpaid_rents",
            field=models.BooleanField(default=True, verbose_name="Notifier les loyers impayés"),
        ),
        migrations.AddField(
            model_name="notificationpreference",
            name="channel_email",
            field=models.BooleanField(default=True, verbose_name="Canal email"),
        ),
        migrations.AddField(
            model_name="notificationpreference",
            name="channel_push",
            field=models.BooleanField(default=True, verbose_name="Canal push"),
        ),
        migrations.AddField(
            model_name="notificationpreference",
            name="channel_sms",
            field=models.BooleanField(default=False, verbose_name="Canal SMS"),
        ),
        migrations.AddField(
            model_name="notificationpreference",
            name="notify_unpaid_rents",
            field=models.BooleanField(default=True, verbose_name="Notifier les loyers impayés"),
        ),
    ]