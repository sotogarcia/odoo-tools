# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import date, datetime, time, timedelta
from logging import getLogger
from copy import deepcopy
from hashlib import blake2b
from slugify import slugify
from typing import List


_logger = getLogger(__name__)

# {
#     facility_id: {
#         "id": facility.id,
#         "name": facility.display_name,
#         "item": facility,
#         "weeks": [
#             "iso_week_number": date_start.today().isocalendar()[1],
#             "date_start": date_start,
#             "date_stop": date_stop,
#             "week_str": self.week_str(...)
#             {
#                 "days": [
#                     {
#                         "iso_week_day": date_start.isoweekday(),
#                         "date_start": date_start,
#                         "date_str": self.date_str(...),
#                         "reservation_count": 0,
#                         "reservations": [
#                             {
#                                 "id": reservation.id,
#                                 "name": reservation.display_name,
#                                 "time_str": self.time_str(...),
#                                 "item": reservation,
#                             }
#                         ]
#                     }
#                 ]
#             }
#         ]
#     }
# }


class ReportFacilityReservations(models.AbstractModel):
    _name = "report.facility_management.report_facility_reservations"
    _description = "List facility reservations between dates"

    _inherit = "time.span.report.mixin"

    def _get_report_values(self, docids, data=None):
        data = data or {}
        docids = data.pop("docids", docids)
        date_start, date_stop, first_day, full_weeks = self._get_options(data)

        if isinstance(date_start, str):
            date_start = fields.Datetime.to_datetime(date_start)
        if isinstance(date_stop, str):
            date_stop = fields.Datetime.to_datetime(date_stop)

        facility_obj = self.env["facility.facility"]
        facility_set = facility_obj.browse(docids)

        datasheet = {}
        self._fill_facilities(datasheet, facility_set)
        self._fill_weeks(
            datasheet, date_start, date_stop, first_day, full_weeks
        )
        self._fill_reservations(datasheet, facility_set, date_start, date_stop)

        docargs = {
            "doc_ids": facility_set.ids,
            "doc_model": "facility.facility",
            "docs": facility_set,
            "data": data,
            "datasheet": datasheet,
            "lang": self.get_lang(),
            "helpers": {"make_html_id": self.make_html_id_deterministic},
        }

        # print(docargs)

        return docargs

    @api.model
    def _get_options(self, data):
        data = data or {}
        context = self.env.context or {}

        today = date.today()
        first_day = self.get_week_start_day(default=0, iso=False)

        values = dict(
            date_start=today,
            date_stop=today,
            first_day=first_day,
            full_weeks=True,
        )

        for key in values.keys():
            dict_key = "report_%s" % key
            if key in data:
                values[key] = data.get(key)
            elif dict_key in context:
                values[key] = context.get(dict_key)

        return (
            values["date_start"],
            values["date_stop"],
            values["first_day"],
            values["full_weeks"],
        )

    @staticmethod
    def _fill_facilities(datasheet, facility_set):
        for facility in facility_set:
            facility_dict = dict(
                id=facility.id,
                name=facility.display_name,
                item=facility,
                weeks=[],
            )

            datasheet[facility.id] = facility_dict

    @api.model
    def _fill_weeks(
        self, datasheet, date_start, date_stop, first_day, full_weeks
    ):
        week_list = self._generate_weeks(
            date_start, date_stop, first_day, full_weeks
        )

        for facility_id, facility_values in datasheet.items():
            facility_values["weeks"] = deepcopy(week_list)

    @api.model
    def _fill_reservations(
        self, datasheet, facility_set, date_start, date_stop
    ):
        reservation_set = self._search_reservations(
            facility_set, date_start, date_stop
        )

        for facility_id, facility_values in datasheet.items():
            for week in facility_values["weeks"]:
                reservation_count = 0
                for day in week["days"]:
                    daily_reservation_set = self._daily_reservations(
                        reservation_set, facility_id, day
                    )

                    for reservation in daily_reservation_set:
                        reservation_count = reservation_count + 1
                        name, description = self._reservation_str(reservation)
                        reservation_values = dict(
                            id=reservation.id,
                            name=name,
                            description=description,
                            time_str=self.time_str(reservation),
                            item=reservation,
                        )
                        day["reservations"].append(reservation_values)

                week["reservation_count"] = reservation_count

    @staticmethod
    def _reservation_str(reservation):
        name = reservation.display_name or reservation.name
        description = reservation.description or reservation.description

        if (not name or not description) and reservation.facility_id:
            facility = reservation.facility_id
            fname = facility.display_name.strip() and facility.name.strip()

            name = name or fname
            description = description or _("Reservation of %s") % fname

        return name, description

    @api.model
    def _search_reservations(self, facilities, date_start, date_stop):
        reservation_obj = self.env["facility.reservation"]

        if not facilities:
            return reservation_obj.browse()

        if isinstance(facilities, models.Model):
            facilities = facilities.ids

        domain = [("facility_id", "in", facilities)]
        order = "date_start ASC, id ASC"
        reservation_set = reservation_obj.search(domain, order=order)

        return reservation_set

    @api.model
    def _generate_weeks(self, date_start, date_stop, first_day, full_weeks):
        week_iterator = self.iter_weeks(
            date_start, date_stop, first_day, full_weeks
        )

        weeks = []
        for date_start, date_stop in week_iterator:
            week_values = dict(
                iso_week_number=date_start.isocalendar()[1],
                date_start=date_start,
                date_stop=date_stop,
                week_str=self.week_str(date_start, first_day),
                days=[],
            )

            # for date_item in self.iter_week(date_start, first_day):
            while date_start <= date_stop:
                day_values = dict(
                    iso_week_day=date_start.isoweekday(),
                    date_start=date_start,
                    date_str=self.date_str(date_start),
                    reservation_count=0,
                    reservations=[],
                )

                week_values["days"].append(day_values)
                date_start = date_start + timedelta(days=1)

            weeks.append(week_values)

        return weeks

    @classmethod
    def _daily_reservations(cls, reservation_set, facility_id, day):
        target = day["date_start"]

        if isinstance(target, date):
            target = datetime.combine(target, time.min)

        return reservation_set.filtered(
            lambda r: r.facility_id.id == facility_id
            and cls.date_in(r, target, True)
        )

    @staticmethod
    def make_html_id_deterministic(
        *parts: object, prefix: str = "id", maxlen: int = 64
    ) -> str:
        """
        Build a safe, deterministic HTML id from stable parts.

        - parts: stable values (e.g., facility_id, ISO year, week start date).
        - prefix: ensures the id starts with a letter.
        - maxlen: cap the length to keep selectors short.
        """

        # 1) Normalize and filter empty inputs
        tokens: List[str] = []
        for p in parts:
            if p is None:
                continue
            s = str(p).strip()
            if not s:
                continue
            tokens.append(slugify(s))  # lowercase, hyphens, no spaces

        # 2) Guarantee at least one token
        if not tokens:
            tokens = ["x"]

        # 3) Join tokens
        base = "-".join(tokens)

        # 4) Short fingerprint to avoid rare collisions
        fp = blake2b(base.encode("utf-8"), digest_size=6).hexdigest()

        # 5) Compose result and cap length
        result = f"{prefix}-{base}-{fp}"

        return result[:maxlen]
