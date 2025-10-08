# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from datetime import timedelta, datetime, date, time
from logging import getLogger
from typing import Iterable, Tuple

from odoo import models, fields, api
from odoo.tools.translate import _, _lt
from odoo.tools.misc import format_date
from pytz import timezone, utc


_logger = getLogger(__name__)


NOT_IMP_MSG = _lt(
    'Abstract method "{}" not implemented in "{}" has been called'
)


class TimeSpanReportMixin(models.AbstractModel):
    """Reusable helpers to build time-span based reports."""

    _name = "time.span.report.mixin"
    _description = "Time span report mixin"

    # ---------------------------- abstract hooks ----------------------------

    def _read_record_values(self, record):
        msg = NOT_IMP_MSG.format("_read_record_values", self._name)
        raise NotImplementedError(msg)

    def _get_report_values(self, docids, data=None):
        msg = NOT_IMP_MSG.format("_get_report_values", self._name)
        raise NotImplementedError(msg)

    # ------------------------------ I/O helpers -----------------------------

    @api.model
    def _get_interval(self, data):
        """Return (date_start, date_stop) from data or context.

        It reads ``data['interval']`` when present, otherwise falls back to
        ``context['time_span']``. If neither is provided, returns ``now``
        for both bounds.
        """
        date_start, date_stop = None, None
        interval = None

        if data:
            interval = data.get("interval")

        if not interval:
            interval = self.env.context.get("time_span")

        if interval:
            date_start = interval.get("date_start")
            if isinstance(date_start, str):
                date_start = fields.Datetime.to_datetime(date_start)

            date_stop = interval.get("date_stop")
            if isinstance(date_stop, str):
                date_stop = fields.Datetime.to_datetime(date_stop)

        if not date_start:
            date_start = fields.Datetime.now()

        if not date_stop:
            date_stop = date_start

        return date_start, date_stop

    # -------------------------------- locale --------------------------------

    @api.model
    def get_lang(self):
        return self.env.context.get("lang") or self.env.user.lang or "es_ES"

    @api.model
    def get_week_start_day(self, default=0, iso=False):
        """Get the first week day from module settings.

        This method retrieves the starting day of the week from the
        system configuration parameter ``facility_management.week_start_day``.
        The parameter value should point to a record in
        ``facility.weekday``. If the parameter is not set, inactive,
        or invalid, the provided ``default`` value will be used.

        Args:
            default (int, optional): Fallback day of the week, expressed
                in Python's ``datetime.weekday()`` style:
                0 = Monday .. 6 = Sunday. Defaults to 0.
            iso (bool, optional): If True, the returned value will use ISO
                numbering (1 = Monday .. 7 = Sunday). If False, the returned
                value will use Python numbering (0 = Monday .. 6 = Sunday).
                Defaults to False.

        Returns:
            int: Weekday number in the requested convention (ISO or Python).
        """
        param_xid = "facility_management.week_start_day"
        param_obj = self.env["ir.config_parameter"].sudo()

        company = self.env.company
        if company is not None:
            param_obj = param_obj.with_company(company)

        param_value = param_obj.get_param(param_xid)
        if param_value and isinstance(param_value, str):
            param_value = (param_value or "0").strip()
            weekday_id = self._safe_cast(param_value, int, 0)
            if weekday_id:
                weekday_obj = self.env["facility.weekday"]
                weekday = weekday_obj.browse(weekday_id)
                if weekday.exists() and weekday.active:
                    return weekday.sequence - (0 if iso else 1)

        return default + (1 if iso else 0)

    @api.model
    def get_timezone_offset(self, dt):
        tzname = self.env.user.tz or utc.zone
        tz = timezone(tzname)

        if dt.tzinfo is None:
            dt = utc.localize(dt)

        return tz.fromutc(dt).utcoffset()

    # ----------------------------- format helpers ---------------------------

    @api.model
    def week_str(self, target_date: date, first_day: int = 0) -> str:
        """Return a localized label like 'Week from Aug 05 to Aug 11'."""

        start = self.midnight(target_date).date()
        start = self.week_start(start, first_day)
        stop = start + timedelta(days=6)

        lang = self.get_lang()
        lstart = format_date(
            self.env, start, lang_code=lang, date_format="MMMM d"
        )
        lstop = format_date(
            self.env, stop, lang_code=lang, date_format="MMMM d"
        )

        return _("Week from {} to {}").format(lstart, lstop)

    @api.model
    def date_str(self, target_date):
        lang = self.get_lang()

        formated = format_date(
            self.env, target_date, lang_code=lang, date_format="EEE, dd-LLL"
        )

        return formated.upper()

    @api.model
    def time_str(self, reservation):
        """Return time span in user's timezone like 'HH:MM-HH:MM'."""

        start = fields.Datetime.context_timestamp(self, reservation.date_start)
        stop = fields.Datetime.context_timestamp(self, reservation.date_stop)

        return "{}-{}".format(start.strftime("%H:%M"), stop.strftime("%H:%M"))

        # tz_offset = self.get_timezone_offset(datetime.utcnow())

        # start = reservation.date_start + tz_offset
        # stop = reservation.date_stop + tz_offset

        # start = start.strftime("%H:%M")
        # stop = stop.strftime("%H:%M")

        # return "{}-{}".format(start, stop)

    # ------------------------------ date logic ------------------------------

    @staticmethod
    def midnight(dt):
        """Return a datetime at 00:00:00 for the given input.
        Accepts either `datetime`, `date`, or parseable values.
        """
        if isinstance(dt, datetime):
            base = dt
        elif isinstance(dt, date):
            base = datetime.combine(dt, time.min)
        else:
            base = fields.Datetime.to_datetime(dt)

        return base.replace(hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    def date_range(cls, date_start, date_stop, full_weeks):
        """Return a list of dates, one-day step, inclusive of bounds.

        If ``full_weeks`` is True the range is expanded to full weeks.
        """
        if full_weeks:
            date_start, date_stop = cls._weekly_interval(date_start, date_stop)

        days = (date_stop - date_start).days + 1
        return [date_start + timedelta(days=v) for v in range(0, days)]

    @staticmethod
    def date_in(reservation, target_date, accept_any_overlap=False):
        next_date = target_date + timedelta(days=1)

        if accept_any_overlap:
            result = (
                reservation.date_start < next_date
                and reservation.date_stop > target_date
            )
        else:
            begin = (
                reservation.date_start >= target_date
                and reservation.date_start < next_date
            )
            finish = (
                reservation.date_stop >= target_date
                and reservation.date_stop < next_date
            )
            result = begin or finish

        return result

    @staticmethod
    def week_day(target_date, iso=False):
        return int(target_date.isoweekday() if iso else target_date.weekday())

    @classmethod
    def week_start(cls, d: date, first_day: int = 0) -> date:
        first = (first_day) % 7
        delta = (d.weekday() - first) % 7
        return d - timedelta(days=delta)

    @classmethod
    def week_end(cls, d: date, first_day: int = 0) -> date:
        ws = cls.week_start(d, first_day)
        return ws + timedelta(days=6)

    @classmethod
    def week_bounds(cls, d: date, first_day: int = 0) -> Tuple[date, date]:
        ws = cls.week_start(d, first_day)
        return ws, ws + timedelta(days=6)

    @classmethod
    def iter_week(cls, d: date, first_day: int = 0) -> Iterable[date]:
        start, _ = cls.week_bounds(d, first_day)
        for i in range(7):
            yield start + timedelta(days=i)

    @classmethod
    def iter_weeks(
        cls, d1: date, d2: date, first_day: int = 0, full_weeks=True
    ) -> Iterable[Tuple[date, date]]:
        """Yield (start, end) week spans between two dates (inclusive)."""
        date_start, date_stop = (d1, d2) if d1 <= d2 else (d2, d1)

        date_start = cls.week_start(date_start, first_day)
        date_stop = cls.week_end(date_stop, first_day)

        if full_weeks:
            while date_start <= date_stop:
                yield date_start, (date_start + timedelta(days=6))
                date_start += timedelta(days=7)
        else:
            while date_start <= date_stop:
                lbound = max(d1, date_start)
                ubound = min(d2, date_start + timedelta(days=6))
                yield lbound, ubound
                date_start += timedelta(days=7)

    # ------------------------------ utils -----------------------------------

    @staticmethod
    def _safe_cast(val, to_type, default=None):
        try:
            return to_type(val)
        except (ValueError, TypeError):
            return default

    # ----------- internal: expand bounds to whole weeks (helper) ------------

    @classmethod
    def _weekly_interval(
        cls, d1: date, d2: date, first_day: int = 0
    ) -> Tuple[date, date]:
        start = cls.week_start(d1, first_day)
        stop = cls.week_end(d2, first_day)
        return start, stop
