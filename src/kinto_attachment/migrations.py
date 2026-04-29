import logging

from kinto.core.storage.postgresql import PostgreSQLPluginMigration
from kinto.core.utils import sqlalchemy as sa


logger = logging.getLogger(__name__)


class KintoAttachmentMigration(PostgreSQLPluginMigration):
    name = "kinto_attachment"
    schema_version = 2

    def migrate_schema(self, start_version, dry_run=False):
        """
        Migrate from 1 to 2.

        If `schema_version` is incremented one day, switch to file based migrations or
        look at `start_version` to run only the relevant SQL commands.
        """
        logger.info(
            f"Migrate PostgreSQL {self.name} from version {start_version} to {self.schema_version}."
        )

        with self.client.connect() as conn:
            result = conn.execute(
                sa.text("""
                SELECT COUNT(*)
                FROM objects
                WHERE parent_id = '__attachments__'
                    AND resource_name = '';
            """)
            )
            existing = result.fetchone()

        logger.info(f"Found {existing[0]} attachment records to migrate.")

        sql = """
        INSERT INTO objects (id, resource_name, parent_id, data)
            SELECT id, 'attachments', parent_id, data
            FROM objects
            WHERE parent_id = '__attachments__' AND resource_name = ''
            ON CONFLICT do nothing;

        DELETE FROM objects
            WHERE parent_id = '__attachments__' AND resource_name = '';

        INSERT INTO metadata (name, value)
            VALUES ('kinto_attachment_schema_version', '2');
        """
        with self.client.connect(force_commit=True) as conn:
            conn.execute(sa.text(sql))
        logger.info(
            f"PostgreSQL {self.name} schema migration {'simulated' if dry_run else 'done'}"
        )
