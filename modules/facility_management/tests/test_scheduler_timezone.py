from datetime import date, datetime

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSchedulerTimezone(TransactionCase):

    def _scheduler(self, tz_name="Europe/Madrid"):
        return self.env["facility.search.available.wizard"].new(
            {"tz": tz_name}
        )

    def test_winter_and_summer(self):
        scheduler = self._scheduler()

        self.assertEqual(
            scheduler.join_datetime(date(2027, 1, 15), 9.0),
            datetime(2027, 1, 15, 8, 0),
        )
        self.assertEqual(
            scheduler.join_datetime(date(2027, 7, 15), 9.0),
            datetime(2027, 7, 15, 7, 0),
        )

    def test_round_trip(self):
        scheduler = self._scheduler()

        utc_dt = scheduler.join_datetime(date(2027, 7, 15), 9.5)
        self.assertEqual(
            scheduler.split_datetime(utc_dt),
            (date(2027, 7, 15), 9.5),
        )

    def test_full_day_dst_transitions(self):
        scheduler = self._scheduler()

        spring_start = scheduler.join_datetime(date(2027, 3, 28), 0.0)
        spring_stop = scheduler.join_datetime(
            date(2027, 3, 28), 24.0, day_limit=True
        )
        self.assertEqual(
            (spring_stop - spring_start).total_seconds(), 23 * 3600
        )

        autumn_start = scheduler.join_datetime(date(2027, 10, 31), 0.0)
        autumn_stop = scheduler.join_datetime(
            date(2027, 10, 31), 24.0, day_limit=True
        )
        self.assertEqual(
            (autumn_stop - autumn_start).total_seconds(), 25 * 3600
        )

    def test_nonexistent_and_ambiguous_local_times(self):
        scheduler = self._scheduler()

        with self.assertRaises(ValidationError):
            scheduler.join_datetime(date(2027, 3, 28), 2.5)

        with self.assertRaises(ValidationError):
            scheduler.join_datetime(date(2027, 10, 31), 2.5)

    def test_explicit_timezone_for_existing_reservation(self):
        mixin = self.env["facility.scheduler.mixin"]

        self.assertEqual(
            mixin.split_datetime(
                datetime(2027, 7, 15, 7, 0),
                tz_name="Europe/Madrid",
            ),
            (date(2027, 7, 15), 9.0),
        )

    def test_timezone_does_not_depend_on_user(self):
        scheduler = self._scheduler("Europe/Madrid").with_context(
            tz="Atlantic/Canary"
        )

        self.assertEqual(
            scheduler.join_datetime(date(2027, 7, 15), 9.0),
            datetime(2027, 7, 15, 7, 0),
        )
