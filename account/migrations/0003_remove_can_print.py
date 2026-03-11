from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_customuser_permissions"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="customuser",
                    name="can_print",
                ),
                migrations.RemoveField(
                    model_name="historicalcustomuser",
                    name="can_print",
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE accounts_customuser DROP COLUMN IF EXISTS can_print",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE accounts_historicalcustomuser DROP COLUMN IF EXISTS can_print",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
