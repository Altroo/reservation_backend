from django.db import migrations


class Migration(migrations.Migration):
    """
    Repair: migration 0002 was recorded as applied but its database operations
    for accounts_historicalcustomuser may not have executed (e.g. table was
    recreated after the fact).  Use ADD COLUMN IF NOT EXISTS so this is safe
    to run on both fresh and already-patched databases.
    Migration 0003 already stripped can_print, so we only add the 4 remaining
    permission columns here.
    """

    dependencies = [
        ("accounts", "0003_remove_can_print"),
    ]

    operations = [
        # Repair customuser table (safe no-op if already present)
        migrations.RunSQL(
            sql="""
                ALTER TABLE accounts_customuser
                    ADD COLUMN IF NOT EXISTS can_view   boolean NOT NULL DEFAULT true;
                ALTER TABLE accounts_customuser
                    ADD COLUMN IF NOT EXISTS can_create boolean NOT NULL DEFAULT false;
                ALTER TABLE accounts_customuser
                    ADD COLUMN IF NOT EXISTS can_edit   boolean NOT NULL DEFAULT false;
                ALTER TABLE accounts_customuser
                    ADD COLUMN IF NOT EXISTS can_delete boolean NOT NULL DEFAULT false;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Repair historicalcustomuser table (this is the column that triggers the error)
        migrations.RunSQL(
            sql="""
                ALTER TABLE accounts_historicalcustomuser
                    ADD COLUMN IF NOT EXISTS can_view   boolean NOT NULL DEFAULT true;
                ALTER TABLE accounts_historicalcustomuser
                    ADD COLUMN IF NOT EXISTS can_create boolean NOT NULL DEFAULT false;
                ALTER TABLE accounts_historicalcustomuser
                    ADD COLUMN IF NOT EXISTS can_edit   boolean NOT NULL DEFAULT false;
                ALTER TABLE accounts_historicalcustomuser
                    ADD COLUMN IF NOT EXISTS can_delete boolean NOT NULL DEFAULT false;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
