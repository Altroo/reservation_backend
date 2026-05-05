from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_fix_historical_permission_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="can_access_hilton_reports",
            field=models.BooleanField(
                default=False, verbose_name="Peut accéder aux rapports Hilton"
            ),
        ),
        migrations.AddField(
            model_name="historicalcustomuser",
            name="can_access_hilton_reports",
            field=models.BooleanField(
                default=False, verbose_name="Peut accéder aux rapports Hilton"
            ),
        ),
    ]
