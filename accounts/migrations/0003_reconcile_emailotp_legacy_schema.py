# Generated to reconcile legacy schema drift for accounts_emailotp
from django.db import migrations


def reconcile_emailotp_schema(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        table_name = "accounts_emailotp"
        tables = connection.introspection.table_names(cursor)
        if table_name not in tables:
            return

        columns = {
            col.name: col
            for col in connection.introspection.get_table_description(cursor, table_name)
        }

        if connection.vendor == "mysql":
            # 1. Drop legacy column 'code' if present
            if "code" in columns:
                cursor.execute(f"ALTER TABLE `{table_name}` DROP COLUMN `code`")

            # 2. Reconcile user_id nullability to allow null (matching EmailOTP.user model field)
            if "user_id" in columns:
                cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `user_id` int(11) NULL")

            # 3. Ensure expected indexes exist if missing
            constraints = connection.introspection.get_constraints(cursor, table_name)
            if "accounts_em_email_5d1e85_idx" not in constraints:
                cursor.execute(
                    f"CREATE INDEX `accounts_em_email_5d1e85_idx` ON `{table_name}` (`email`, `purpose`, `is_used`)"
                )
            if "accounts_em_created_46961d_idx" not in constraints:
                cursor.execute(
                    f"CREATE INDEX `accounts_em_created_46961d_idx` ON `{table_name}` (`created_at`)"
                )
        elif connection.vendor == "sqlite":
            if "code" in columns:
                try:
                    cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN code")
                except Exception:
                    pass
        elif connection.vendor == "postgresql":
            if "code" in columns:
                cursor.execute(f'ALTER TABLE "{table_name}" DROP COLUMN "code"')
            if "user_id" in columns:
                cursor.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "user_id" DROP NOT NULL')


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(
            reconcile_emailotp_schema,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
