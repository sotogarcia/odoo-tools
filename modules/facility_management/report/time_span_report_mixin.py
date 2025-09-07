# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from datetime import timedelta, datetime, date
from logging import getLogger
from typing import Iterable, Tuple

from odoo import models, fields, api
from odoo.tools.translate import _, _lt
from pytz import timezone, utc


_logger = getLogger(__name__)


NOT_IMP_MSG = _lt(
    "Abstract method «{}» not implemented in «{}» has been called"
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
        lang = self.env.context.get("lang")
        if not lang:
            uid = self.env.context.get("uid")
            user = (
                self.env["res.users"].browse(uid)
                if uid else self.env.ref("base.user_root")
            )
            lang = user.lang if user else "es_ES"
        return lang

    @api.model
    def getweek_start_day(self, default=1, iso=False):
        """Return first weekday index (0=Mon .. 6=Sun by default)."""
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
                    return weekday.sequence

        return default + (1 if iso else 0)

    @api.model
    def get_timezone_offset(self, dt):
        tz = self.env.user.tz or utc.zone
        tz = timezone(tz)
        return tz.fromutc(dt).utcoffset()

    # ----------------------------- format helpers ---------------------------

    @classmethod
    def week_str(cls, target_date):
        """Return a human label like "Week from Aug 05 to Aug 11"."""
        date_format = _("%B, %d")

        date_start = cls.midnight(target_date)
        date_stop = cls.midnight(target_date)

        offset = cls.week_day(date_start)
        date_start = date_start - timedelta(days=offset)
        date_stop = date_start + timedelta(days=6)

        date_start = date_start.strftime(date_format)
        date_stop = date_stop.strftime(date_format)

        return _("Week from {} to {}").format(date_start, date_stop)

    @staticmethod
    def date_str(target_date):
        return target_date.strftime("%a, %d-%b").upper()

    @api.model
    def time_str(self, reservation):
        tz_offset = self.get_timezone_offset(datetime.utcnow())

        start = reservation.date_start + tz_offset
        stop = reservation.date_stop + tz_offset

        start = start.strftime("%H:%M")
        stop = stop.strftime("%H:%M")

        return "{}-{}".format(start, stop)

    # ------------------------------ date logic ------------------------------

    @staticmethod
    def midnight(dt):
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

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
    def date_in(reservation, target_date):
        next_date = target_date + timedelta(days=1)
        begin = (
            reservation.date_start >= target_date and
            reservation.date_start < next_date
        )
        finish = (
            reservation.date_stop >= target_date and
            reservation.date_stop < next_date
        )
        return begin or finish

    @staticmethod
    def week_day(target_date, iso=False):
        return int(
            target_date.isoweekday() if iso else target_date.weekday()
        )

    @classmethod
    def week_start(cls, d: date, first_day: int) -> date:
        first = (first_day) % 7
        delta = (d.weekday() - first) % 7
        return d - timedelta(days=delta)

    @classmethod
    def week_end(cls, d: date, first_day: int) -> date:
        ws = cls.week_start(d, first_day)
        return ws + timedelta(days=6)

    @classmethod
    def week_bounds(cls, d: date, first_day: int) -> Tuple[date, date]:
        ws = cls.week_start(d, first_day)
        return ws, ws + timedelta(days=6)

    @classmethod
    def iter_week(cls, d: date, first_day: int) -> Iterable[date]:
        start, _ = cls.week_bounds(d, first_day)
        for i in range(7):
            yield start + timedelta(days=i)

    @classmethod
    def iter_weeks(
        cls, d1: date, d2: date, first_day: int, full_weeks=True
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
    def _weekly_interval(cls, d1: date, d2: date) -> Tuple[date, date]:
        first_day = 0  # Monday
        start = cls.week_start(d1, first_day)
        stop = cls.week_end(d2, first_day)
        return start, stop
