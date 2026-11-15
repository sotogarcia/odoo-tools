"""Preserve the legacy stored stop-time column before making it computed."""


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'facility_reservation_scheduler'
           AND column_name = 'time_stop'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            ALTER TABLE facility_reservation_scheduler
            RENAME COLUMN time_stop TO legacy_time_stop
            """
        )
