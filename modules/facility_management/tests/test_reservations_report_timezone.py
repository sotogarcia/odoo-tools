from datetime import date, datetime, timedelta
from types import SimpleNamespace

from odoo.tests.common import TransactionCase


class FakeReservations(list):

    def filtered(self, predicate):
        return FakeReservations(record for record in self if predicate(record))


class TestReservationsReportTimezone(TransactionCase):

    def setUp(self):
        super().setUp()
        user = self.env["res.users"].create(
            {
                "name": "Facility report timezone test",
                "login": "facility_report_timezone_test",
                "tz": "Europe/Madrid",
            }
        )
        self.report = self.env[
            "report.facility_management.report_facility_reservations"
        ].with_user(user)

    def test_local_day_bounds_in_winter_and_summer(self):
        self.assertEqual(
            self.report.day_bounds_utc(date(2027, 1, 15)),
            (
                datetime(2027, 1, 14, 23, 0),
                datetime(2027, 1, 15, 23, 0),
            ),
        )
        self.assertEqual(
            self.report.day_bounds_utc(date(2027, 7, 15)),
            (
                datetime(2027, 7, 14, 22, 0),
                datetime(2027, 7, 15, 22, 0),
            ),
        )

    def test_day_bounds_during_dst_transitions(self):
        spring_start, spring_stop = self.report.day_bounds_utc(
            date(2027, 3, 28)
        )
        self.assertEqual(
            (spring_stop - spring_start).total_seconds(), 23 * 3600
        )

        autumn_start, autumn_stop = self.report.day_bounds_utc(
            date(2027, 10, 31)
        )
        self.assertEqual(
            (autumn_stop - autumn_start).total_seconds(), 25 * 3600
        )

    def test_reservation_is_grouped_by_local_day(self):
        reservation = SimpleNamespace(
            facility_id=SimpleNamespace(id=5),
            date_start=datetime(2027, 7, 14, 22, 30),
            date_stop=datetime(2027, 7, 14, 23, 30),
        )
        reservations = FakeReservations([reservation])

        self.assertFalse(
            self.report._daily_reservations(
                reservations, 5, {"date_start": date(2027, 7, 14)}
            )
        )
        self.assertEqual(
            self.report._daily_reservations(
                reservations, 5, {"date_start": date(2027, 7, 15)}
            ),
            [reservation],
        )
        self.assertFalse(
            self.report._daily_reservations(
                reservations, 6, {"date_start": date(2027, 7, 15)}
            )
        )

    def test_timezone_offset_accepts_utc_naive_datetime(self):
        self.assertEqual(
            self.report.get_timezone_offset(datetime(2027, 7, 15, 12)),
            timedelta(hours=2),
        )
