from datetime import date, datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSchedulerOvernight(TransactionCase):

    def _scheduler(self, **values):
        values = {
            "tz": "Europe/Madrid",
            "date_base": date(2027, 1, 15),
            "time_start": 22.0,
            "date_delay": 4.0,
            "full_day": False,
            **values,
        }
        return self.env["facility.search.available.wizard"].new(values)

    def test_overnight_interval_and_displayed_stop(self):
        scheduler = self._scheduler()
        start, stop = scheduler.compute_interval(scheduler.date_base)

        self.assertEqual(start, datetime(2027, 1, 15, 21, 0))
        self.assertEqual(stop, datetime(2027, 1, 16, 1, 0))
        self.assertEqual(scheduler.time_stop, 2.0)

    def test_multi_day_interval(self):
        scheduler = self._scheduler(date_delay=28.0)
        start, stop = scheduler.compute_interval(scheduler.date_base)

        self.assertEqual(stop - start, timedelta(hours=28))
        self.assertEqual(scheduler.time_stop, 2.0)

    def test_spring_transition_keeps_real_duration(self):
        scheduler = self._scheduler(
            date_base=date(2027, 3, 27),
            time_start=23.0,
            date_delay=4.0,
        )
        start, stop = scheduler.compute_interval(scheduler.date_base)

        self.assertEqual(stop - start, timedelta(hours=4))
        self.assertEqual(
            scheduler.split_datetime(stop),
            (date(2027, 3, 28), 4.0),
        )

    def test_autumn_transition_keeps_real_duration(self):
        scheduler = self._scheduler(
            date_base=date(2027, 10, 30),
            time_start=23.0,
            date_delay=4.0,
        )
        start, stop = scheduler.compute_interval(scheduler.date_base)

        self.assertEqual(stop - start, timedelta(hours=4))
        self.assertEqual(
            scheduler.split_datetime(stop),
            (date(2027, 10, 31), 2.0),
        )

    def test_full_day_preserves_local_midnights(self):
        scheduler = self._scheduler(
            date_base=date(2027, 3, 28),
            full_day=True,
        )
        start, stop = scheduler.compute_interval(scheduler.date_base)
        self.assertEqual(stop - start, timedelta(hours=23))

        scheduler.date_base = date(2027, 10, 31)
        start, stop = scheduler.compute_interval(scheduler.date_base)
        self.assertEqual(stop - start, timedelta(hours=25))

    def test_recurrence_preserves_local_start(self):
        scheduler = self._scheduler(
            date_base=date(2027, 3, 27),
            time_start=23.0,
            repeat=True,
            interval_type="day",
            interval_number=1,
            finish_type="number",
            finish_number=3,
        )
        dates = scheduler.scheduled_dates()
        self.assertEqual(
            dates,
            [date(2027, 3, 27), date(2027, 3, 28), date(2027, 3, 29)],
        )

        intervals = [scheduler.compute_interval(day) for day in dates]
        for day, (start, stop) in zip(dates, intervals):
            self.assertEqual(
                scheduler.split_datetime(start),
                (day, 23.0),
            )
            self.assertEqual(stop - start, timedelta(hours=4))

    def test_nonexistent_local_start_rejected(self):
        scheduler = self._scheduler(
            date_base=date(2027, 3, 28),
            time_start=2.5,
        )
        with self.assertRaises(ValidationError):
            scheduler.compute_interval(scheduler.date_base)

    def test_invalid_duration_rejected(self):
        scheduler = self._scheduler(date_delay=0.0)
        with self.assertRaises(ValidationError):
            scheduler._check_date_delay()
