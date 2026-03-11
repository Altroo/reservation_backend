from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        # CustomUser fields
        migrations.AddField(
            model_name="customuser",
            name="can_view",
            field=models.BooleanField(default=True, verbose_name="Peut consulter"),
        ),
        migrations.AddField(
            model_name="customuser",
            name="can_print",
            field=models.BooleanField(default=True, verbose_name="Peut imprimer"),
        ),
        migrations.AddField(
            model_name="customuser",
            name="can_create",
            field=models.BooleanField(default=False, verbose_name="Peut créer"),
        ),
        migrations.AddField(
            model_name="customuser",
            name="can_edit",
            field=models.BooleanField(default=False, verbose_name="Peut modifier"),
        ),
        migrations.AddField(
            model_name="customuser",
            name="can_delete",
            field=models.BooleanField(default=False, verbose_name="Peut supprimer"),
        ),
        # HistoricalCustomUser mirror fields (required by simple_history)
        migrations.AddField(
            model_name="historicalcustomuser",
            name="can_view",
            field=models.BooleanField(default=True, verbose_name="Peut consulter"),
        ),
        migrations.AddField(
            model_name="historicalcustomuser",
            name="can_print",
            field=models.BooleanField(default=True, verbose_name="Peut imprimer"),
        ),
        migrations.AddField(
            model_name="historicalcustomuser",
            name="can_create",
            field=models.BooleanField(default=False, verbose_name="Peut créer"),
        ),
        migrations.AddField(
            model_name="historicalcustomuser",
            name="can_edit",
            field=models.BooleanField(default=False, verbose_name="Peut modifier"),
        ),
        migrations.AddField(
            model_name="historicalcustomuser",
            name="can_delete",
            field=models.BooleanField(default=False, verbose_name="Peut supprimer"),
        ),
    ]
