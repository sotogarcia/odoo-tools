from datetime import date, datetime, timedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDemoReservationScheduler(TransactionCase):

    def setUp(self):
        super().setUp()
        self.scheduler = self.env.ref(
            "facility_management.facility_reservation_scheduler_demo_1",
            raise_if_not_found=False,
        )
        if not self.scheduler:
            self.skipTest("Facility management demo data is not installed")

    def test_demo_scheduler_recurrence_and_timezone(self):
        scheduler = self.scheduler
        expected_days = [
            date(2020, 1, 6),
            date(2020, 1, 8),
            date(2020, 1, 10),
            date(2020, 1, 20),
            date(2020, 1, 22),
            date(2020, 1, 24),
            date(2020, 2, 3),
        ]

        self.assertEqual(scheduler.tz, "Europe/Madrid")
        self.assertEqual(scheduler.date_base, date(2020, 1, 6))
        self.assertEqual(scheduler.scheduled_dates(), expected_days)
        self.assertEqual(scheduler.facility_id, self.env.ref(
            "facility_management.facility_classroom_3"
        ))

        reservations = scheduler.reservation_ids.sorted("date_start")
        self.assertEqual(len(reservations), 7)
        for day, reservation in zip(expected_days, reservations):
            self.assertEqual(
                reservation.date_start,
                datetime.combine(day, datetime.min.time())
                + timedelta(hours=8),
            )
            self.assertEqual(
                reservation.date_stop,
                reservation.date_start + timedelta(hours=2),
            )
            self.assertEqual(reservation.state, "confirmed")
            self.assertTrue(reservation.validate)
            self.assertTrue(reservation.active)
            self.assertEqual(reservation.facility_id, scheduler.facility_id)

    def test_demo_scheduler_recalculation_is_idempotent(self):
        scheduler = self.scheduler
        original_ids = set(scheduler.reservation_ids.ids)

        scheduler.make_reservations()
        self.assertEqual(set(scheduler.reservation_ids.ids), original_ids)
        self.assertEqual(len(scheduler.reservation_ids), 7)

    def test_demo_individual_reservations_are_fixed_in_2020(self):
        expected = [
            ("facility_reservation_1", datetime(2020, 1, 7, 16)),
            ("facility_reservation_2", datetime(2020, 1, 8, 19)),
            ("facility_reservation_3", datetime(2020, 1, 8, 19)),
        ]
        for xmlid, date_start in expected:
            reservation = self.env.ref("facility_management." + xmlid)
            self.assertEqual(reservation.date_start, date_start)
            self.assertEqual(
                reservation.date_stop, date_start + timedelta(hours=2)
            )
