"""Convert existing wall-clock stop times into elapsed UTC durations."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    scheduler_obj = env["facility.reservation.scheduler"].with_context(
        active_test=False
    )

    cr.execute(
        """
        SELECT id, legacy_time_stop
          FROM facility_reservation_scheduler
        """
    )
    legacy_times = dict(cr.fetchall())

    for scheduler in scheduler_obj.browse(list(legacy_times)).exists():
        if scheduler.full_day:
            # Full days are calendar-based; their actual duration is
            # computed per occurrence to handle daylight-saving changes.
            duration = 24.0
        else:
            date_start = scheduler.join_datetime(
                scheduler.date_base,
                scheduler.time_start,
                day_limit=True,
            )
            date_stop = scheduler.join_datetime(
                scheduler.date_base,
                legacy_times[scheduler.id],
                day_limit=True,
            )
            duration = (date_stop - date_start).total_seconds() / 3600.0

        cr.execute(
            """
            UPDATE facility_reservation_scheduler
               SET date_delay = %s
             WHERE id = %s
            """,
            (duration, scheduler.id),
        )

    env.invalidate_all()
