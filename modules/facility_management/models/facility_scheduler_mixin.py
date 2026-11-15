###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


from datetime import date, datetime, time, timedelta
from itertools import islice
from logging import getLogger
from math import ceil, floor

from dateutil.relativedelta import relativedelta
from dateutil.rrule import (
    DAILY,
    MO,
    MONTHLY,
    WEEKLY,
    YEARLY,
    rrule,
    weekday,
)
from num2words import num2words
from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import AND, OR
from odoo.tools.translate import _
from pytz import (
    AmbiguousTimeError,
    NonExistentTimeError,
    timezone,
    utc,
)

_logger = getLogger(__name__)


class FacilitySchedulerMixin(models.AbstractModel):
    """Provides the necessary functionality to schedule dates"""

    _name = "facility.scheduler.mixin"
    _description = "Provides the necessary functionality to schedule dates"

    # =============================================================================
    # Schedule configuration
    # =============================================================================

    # -- Date and timezone ------------------------------------------------------

    date_base = fields.Date(
        string="Date",
        required=True,
        readonly=False,
        index=False,
        default=lambda self: fields.Date.context_today(self),
        help="Date of reservation start",
    )

    @api.onchange("date_base")
    def _onchange_date_base(self):
        out_msg = _("Schedule time out of training action timespan")
        weekday_msg = _(
            "Day of the week corresponding to the start date "
            "is not among the selected days of the week"
        )

        if self._field_changed("field_date_base"):
            # date_base+time_start within the training action time range
            if not self._in_time_range(which="left"):
                return self._warn(out_msg)

            # day of the week corresponds to the date_base
            if self.interval_type == "week" and not self._match_weekday(
                self.date_base
            ):
                self._ensure_weekday()
                return self._warn(weekday_msg)

            # date_base less than or equal to finish_date
            self.finish_date = max(self.date_base, self.finish_date)

    tz = fields.Selection(
        string="Timezone",
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.env.user.tz or "UTC",
        help="Timezone used to interpret the schedule's local dates and times",
        selection=_tz_get,
    )

    # -- Time and duration ------------------------------------------------------

    time_start = fields.Float(
        string="Time start",
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.default_time_start(),
        digits=(16, 2),
        help="Time of reservation start",
    )

    @api.onchange("time_start")
    def _onchange_time_start(self):
        out_msg = _("Schedule time out of training action timespan")

        if self._field_changed("field_time_start") and not self.full_day:
            # Within the day
            if self.time_start < 0:
                self.time_start = 0
            elif self.time_start > 23 + (59 / 60):
                self.time_start = 23 + (59 / 60)

            self.time_start = self.round_m(self.time_start, (1 / 60), "down")

            # Less than time_stop
            if self.time_start > self.time_stop:
                self.time_stop = self.round_m(
                    self.time_start + (1 / 60), (1 / 60), "down"
                )

            # date_base+time_start within the training action time range
            if not self._in_time_range(which="left"):
                return self._warn(out_msg)

    def default_time_start(self):
        now = datetime.utcnow()  # noqa: DTZ003

        tz = self.env.user.tz or utc.zone
        tz = timezone(tz)
        now_tz = tz.fromutc(now)

        return float(now_tz.hour)

    time_stop = fields.Float(
        string="Time stop",
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.default_time_start() + 1.0,
        digits=(16, 2),
        help="Time of reservation stop",
    )

    @api.onchange("time_stop")
    def _onchange_time_stop(self):
        out_msg = _("Schedule time out of training action timespan")
        min_date_delay = _("Session must last at least one minute")

        if self._field_changed("field_time_stop") and not self.full_day:
            # Within the day
            if self.time_stop < 0:
                self.time_stop = self.time_start + (1 / 60)
            elif self.time_stop >= 24:
                self.time_stop = 23 + (59 / 60)

            self.time_stop = self.round_m(self.time_stop, (1 / 3600), "down")

            # Less than time_start
            if self.time_stop < self.time_start + (1 / 60):
                return self._warn(min_date_delay)

            # fisnish_date+time_stop within the training action time range
            if not self._in_time_range(which="right"):
                return self._warn(out_msg)

    full_day = fields.Boolean(
        string="Full day",
        required=False,
        readonly=False,
        index=False,
        default=False,
        help="If checked, facility will be reserved for the entire day",
    )

    @api.onchange("full_day")
    def _onchange_full_day(self):
        out_msg = _("Schedule time out of training action timespan")

        if self._field_changed("field_full_day") and not self._in_time_range(
            which="both"
        ):
            return self._warn(out_msg)

    date_delay = fields.Float(
        string="Duration",
        required=True,
        readonly=False,
        index=False,
        default=0.0,
        digits=(16, 2),
        help="Time length of the reservation",
        store=False,
        compute="_compute_date_delay",
    )

    @api.depends("full_day", "date_base", "time_start", "time_stop")
    def _compute_date_delay(self):
        for record in self:
            if record.full_day:
                record.date_delay = 24.0
            else:
                start = record.join_datetime(
                    record.date_base, record.time_start, day_limit=True
                )

                stop = record.join_datetime(
                    record.date_base, record.time_stop, day_limit=True
                )

                record.date_delay = self._float_interval(start, stop)

    @api.onchange("date_delay")
    def _onchange_date_delay(self):
        for record in self:
            if (
                not record.full_day
                and record._origin.date_delay != record.date_delay
            ):
                record.time_stop = record.time_start + record.date_delay

    # -- Day descriptions -------------------------------------------------------

    weekday = fields.Char(
        string="Weekday",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Weekday name",
        size=50,
        translate=True,
        compute="_compute_week_day",
    )

    @api.depends("date_base")
    def _compute_week_day(self):
        for record in self:
            if record.date_base:
                record.weekday = record.date_base.strftime("%A").title()
            else:
                record.weekday = None

    # =============================================================================
    # Recurrence configuration
    # =============================================================================

    # -- Frequency and weekdays ------------------------------------------------

    repeat = fields.Boolean(
        string="Repeat",
        required=False,
        readonly=False,
        index=False,
        default=False,
        help="If checked, reservation will be repeated over time",
    )

    interval_number = fields.Integer(
        string="Repeat every",
        required=True,
        readonly=False,
        index=False,
        default=1,
        help="Numeric value for repeat interval",
    )

    @api.onchange("interval_number")
    def _onchange_interval_number(self):
        min_interval_msg = _(
            "Interval number must be greater than or equal to one"
        )

        if (
            self._field_changed("field_interval_number")
            and self.interval_number < 1
        ):
            self.interval_number = 1
            return self._warn(min_interval_msg)

    interval_type = fields.Selection(
        string="Interval type",
        required=True,
        readonly=False,
        index=False,
        default="week",
        help=(
            "Defines the unit of time used between repetitions "
            "(day, week, month, or year)"
        ),
        selection=[
            ("day", "Days"),
            ("week", "Weeks"),
            ("month", "Months"),
            ("year", "Years"),
        ],
    )

    @api.onchange("interval_type", "weekday_ids")
    def _onchange_interval_type(self):
        weekday_msg = _(
            "Day of the week corresponding to the start date "
            "is not among the selected days of the week"
        )

        if (
            self._field_changed("field_interval_type")
            and self.interval_type == "week"
            and not self._match_weekday(self.date_base)
        ):
            self._ensure_weekday()
            return self._warn(weekday_msg)

    weekday_ids = fields.Many2many(
        string="Weekdays",
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.default_weekday_ids(),
        help="Days of the week on which it is repeated",
        comodel_name="facility.weekday",
        # relation= <-- This must to be empty to allow inheritance
        column1="target_id",
        column2="weekday_id",
        domain=[],
        context={},
    )

    def default_weekday_ids(self):
        week_day_domain = [("workday", "=", True)]
        week_day_obj = self.env["facility.weekday"]
        return week_day_obj.search(week_day_domain)

    @api.constrains("weekday_ids")
    def _check_weekday_ids(self):
        msg1 = _("You must choose at least one day of the week")
        msg2 = _(
            "The day of the week corresponding to the start date is not "
            "among the selected days of the week"
        )

        for record in self:
            if record.interval_type == "week":
                if not record.weekday_ids:
                    raise ValidationError(msg1)

                if not record._match_weekday(record.date_base):
                    raise ValidationError(msg2)

    # -- Monthly recurrence -----------------------------------------------------

    month_type = fields.Selection(
        string="Month type",
        required=True,
        readonly=False,
        index=True,
        default="week",
        help="Monthly recurrence type",
        selection=[("week", "Weekday"), ("month", "Month day")],
    )

    week_day_str = fields.Char(
        string="Weekday name",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Name of the current weekday and repeat order in month",
        size=50,
        translate=True,
        compute="_compute_week_day_str",
    )

    @api.depends("date_base")
    def _compute_week_day_str(self):
        for record in self:
            day_name = record.date_base.strftime("%A").title()
            nth = record.nth_weekday().title()

            record.week_day_str = f"{day_name} ({nth})"

    # -- Recurrence limits ------------------------------------------------------

    finish_type = fields.Selection(
        string="Finish",
        required=True,
        readonly=False,
        index=False,
        default="number",
        help=(
            "Defines when the repetition should stop: after a number of "
            "occurrences or when reaching a specific date"
        ),
        selection=[("number", "After repeating"), ("date", "When passing")],
    )

    finish_date = fields.Date(
        string="Finish date",
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self._next_month(),
        help="Date of the last repetition",
    )

    @api.onchange("finish_date")
    def _onchange_finish_date(self):
        out_msg = _("Schedule time out of training action timespan")
        min_finish_date = _("Finish date cannot be less than start date")

        if self._field_changed("field_finish_date"):
            # date_base+time_start within the training action time range
            if not self._in_time_range(which="right"):
                return self._warn(out_msg)

            # date_base less than or equal to finish_date
            if self.finish_date < self.date_base:
                self.finish_date = self.date_base
                return self._warn(min_finish_date)

    finish_number = fields.Integer(
        string="Repetitions",
        required=True,
        readonly=False,
        index=False,
        default=5,
        help="Total number of repetitions",
    )

    @api.onchange("finish_number")
    def _onchange_finish_number(self):
        message = _("Finish number must be greater than or equal to one")

        finish_number_changed = self._field_changed("field_finish_number")
        if finish_number_changed and self.finish_number < 1:
            self.finish_number = 1
            return self._warn(message)

    # -- Next scheduled occurrence ---------------------------------------------

    next_schedule = fields.Datetime(
        string="Next schedule",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Display next schedule date/time",
        compute="_compute_next_schedule",
    )

    @api.depends(
        "date_base",
        "time_start",
        "time_stop",
        "full_day",
        "repeat",
        "interval_number",
        "interval_type",
        "finish_type",
        "finish_date",
        "finish_number",
        "weekday_ids",
        "month_type",
        "tz",
    )
    def _compute_next_schedule(self):
        for record in self:
            next_date = record._next_repetition_date(record.date_base)

            if next_date:
                time_start = 0.0 if record.full_day else record.time_start
                record.next_schedule = record.join_datetime(
                    next_date,
                    time_start,
                    day_limit=True,
                )
            else:
                record.next_schedule = False

    # =============================================================================
    # Constraints
    # =============================================================================

    _sql_constraints = [  # noqa: RUF012
        (
            "positive_interval",
            "CHECK(time_start < time_stop)",
            "Reservation cannot finish before it starts",
        ),
        (
            "positive_interval_number",
            "CHECK(repeat <> True or interval_number > 0)",
            "Interval number must be greater than zero",
        ),
        (
            "positive_finish_number",
            "CHECK(finish_type <> 'number' or finish_number > 0)",
            "The total number of repetitions must be greater than zero",
        ),
        (
            "finish_after_begins",
            "CHECK(finish_date >= date_base)",
            "The end date must be after the start date",
        ),
    ]

    # =============================================================================
    # Recurrence calculation
    # =============================================================================

    # -- Date and weekday helpers ----------------------------------------------

    def _next_month(self):
        return fields.Date.context_today(self) + relativedelta(months=1)

    @api.model
    def nth_weekday(self):
        target = self.date_base

        mixin = self.env["time.span.report.mixin"]

        weekday = target.weekday()

        day_one = target - timedelta(target.day - 1)
        date_range = mixin.date_range(day_one, target, full_weeks=False)
        cardinal = len([dt for dt in date_range if dt.weekday() == weekday])

        lang = mixin.get_lang() or "es_ES"

        return num2words(cardinal, to="ordinal", lang=lang)

    # -- Rule definition --------------------------------------------------------

    def _get_recurrence_rule(self):
        self.ensure_one()

        frequencies = {
            "day": DAILY,
            "week": WEEKLY,
            "month": MONTHLY,
            "year": YEARLY,
        }

        if self.interval_number < 1:
            raise ValidationError(
                _("Interval number must be greater than zero")
            )

        if self.finish_type == "number" and self.finish_number < 1:
            raise ValidationError(_("Finish number must be greater than zero"))

        params = {
            "dtstart": datetime.combine(self.date_base, time.min),
            "interval": self.interval_number,
        }

        if self.interval_type == "week":
            weekdays = self.weekday_ids.mapped("sequence")

            if not weekdays:
                raise ValidationError(
                    _("You must choose at least one day of the week")
                )

            params["byweekday"] = [weekday(day - 1) for day in weekdays]
            params["wkst"] = MO

        elif self.interval_type == "month":
            if self.month_type == "month":
                params["bymonthday"] = self.date_base.day

            else:
                position = (self.date_base.day - 1) // 7 + 1
                day = self.date_base.weekday()

                params["byweekday"] = weekday(day, position)

        if self.finish_type == "number":
            params["count"] = self.finish_number

        else:
            params["until"] = datetime.combine(self.finish_date, time.max)

        return rrule(
            frequencies[self.interval_type],
            **params,
        )

    # -- Weekday matching -------------------------------------------------------

    def _match_weekday(self, date_cursor):
        sequences = self.mapped("weekday_ids.sequence")
        return date_cursor.isoweekday() in sequences

    def _search_weekday_for(self, date_cursor):
        """Search for facility.weekday which sequence match with given
        date_cursor weekday.
        IMPORTANT: This method is provided so that it can be used in
        specializations of this class

        Args:
            date_cursor (date): date or datetime to search matching weekday

        Returns:
            models.Model: allways returns a facility.weekday recordset.
        """

        weekday_sequence = date_cursor.weekday() + 1

        weekday_domain = [("sequence", "=", weekday_sequence)]
        weekday_obj = self.env["facility.weekday"]
        weekday = weekday_obj.search(weekday_domain, limit=1)

        return weekday

    def _ensure_weekday(self):
        """Ensure date_base weekday is choosen in weekday_ids"""
        for record in self:
            weekday = self._search_weekday_for(record.date_base)
            if weekday and weekday not in self.weekday_ids:
                record.weekday_ids = [(4, weekday.id, 0)]

    # -- Occurrence generation --------------------------------------------------

    @staticmethod
    def _loop_security_break(index, limit=1024):
        if index >= limit:
            msg = _("Security loop limit for reservations ({}) exceeded")
            raise UserError(msg.format(limit))

        return index + 1

    def _next_repetition_date(self, date_cursor):
        self.ensure_one()

        rule = self._get_recurrence_rule()

        current = datetime.combine(date_cursor, time.min)
        result = rule.after(current, inc=False)

        return result.date() if result else False

    def _compute_repetition_dates(self):
        self.ensure_one()

        rule = self._get_recurrence_rule()

        dates = [dt.date() for dt in islice(rule, 1025)]

        if len(dates) > 1024:
            self._loop_security_break(1024)

        return dates

    # =============================================================================
    # Reservation interval matching
    # =============================================================================

    # -- Overlap domain ---------------------------------------------------------

    def _overlapped_domain(self, f1, f2, v1, v2, inverse=False):
        """Create a valid Odoo domain to search reservations whose time
        intervals, given by its limits, overlap with the given time interval.

                           F1                 F2
                           ├──────────────────┤···

            V1   V2    V1   V2    V1    V2   V1   V2   V1    V2
            ╟─────╢    ╟─────╢    ╟─────╢    ╟─────╢    ╟─────╢
              OUT                   IN                    OUT
                         V1                     V2
                         ╟──────────────────────╢

            APPLYING THE LAWS OF MORGAN
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
            OUT => O(F1 >= V2, F2 <= V1)
            IN = NO(OUT) => NO(O(F1 >= V2, F2 <= V1)) => Y(F1 < V2, F2 > V1)

        Avgs:
            f1 (str): name of the field in the lower limit of the left range
            f2 (str): name of the field in the upper limit of the left range
            v1 (str): value at the lower limit of the right range
            v2 (str): value at the upper limit of the right range
            inverse (bool): if value is TRUE then the resulting domain will
            serve to find the NOT overlapping reservations
        """

        if inverse:
            op1, op2, op3 = "|", ">=", "<="
        else:
            op1, op2, op3 = "&", "<", ">"

        return [op1, (f1, op2, v2), (f2, op3, v1)]

    # =============================================================================
    # Timezone conversion
    # =============================================================================

    @api.model
    def _get_scheduler_timezone(self, tz_name=None):
        if not tz_name:
            self.ensure_one()
            tz_name = self.tz

        return timezone(tz_name or "UTC")

    @api.model
    def join_datetime(self, dt, tm=0.0, day_limit=False):
        """Combine a local date and time, returning a UTC datetime."""

        dt = dt or date.min
        tm = tm or 0.0

        if day_limit:
            tm = min(tm, 24)

        local_dt = datetime.combine(dt, time.min) + timedelta(
            seconds=tm * 3600.0
        )

        tz = self._get_scheduler_timezone()

        try:
            localized_dt = tz.localize(local_dt, is_dst=None)
        except NonExistentTimeError as exc:
            raise ValidationError(
                _(
                    "The selected local time does not exist due to a daylight saving time change."
                )
            ) from exc
        except AmbiguousTimeError as exc:
            raise ValidationError(
                _(
                    "The selected local time is ambiguous due to a daylight saving time change."
                )
            ) from exc

        return localized_dt.astimezone(utc).replace(tzinfo=None)

    @api.model
    def split_datetime(self, dt, tz_name=None):
        """Convert a UTC datetime into a local date and float time."""

        if isinstance(dt, str):
            dt = fields.Datetime.from_string(dt)

        if dt.tzinfo is None:
            dt = utc.localize(dt)

        tz = self._get_scheduler_timezone(tz_name=tz_name)
        local_dt = dt.astimezone(tz)

        local_date = local_dt.date()
        local_time = (
            local_dt.hour
            + local_dt.minute / 60.0
            + local_dt.second / 3600.0
            + local_dt.microsecond / 3600000000.0
        )

        return local_date, local_time

    # =============================================================================
    # Reservation scheduling and availability
    # =============================================================================

    # -- Scheduled dates --------------------------------------------------------

    def scheduled_dates(self):
        """Return all the dates, whithout time, that will be resulting from
        the  criteria of the scheduler.

        Returns:
            list: a list of dates (whithout time)
        """

        self.ensure_one()

        if self.repeat:
            return self._compute_repetition_dates()
        else:
            return [self.date_base]

    # -- Reservation search -----------------------------------------------------

    def matching_reservations(self, not_confirmed=False):
        """Search for reservations search for reservations that match the
        dates of the schedule.

        Args:
            not_confirmed (bool, optional): if value is TRUE then it searches
            both confirmed and unconfirmed reservations, otherwise it only
            searches the first ones.

        Returns:
            model.Model: returns the set of matching records
        """

        self.ensure_one()

        dates = self.scheduled_dates()

        time_start = 0.0 if self.full_day else self.time_start
        time_stop = 24.0 if self.full_day else self.time_stop

        domains = []

        for dt in dates:
            v1 = self.join_datetime(dt, time_start, day_limit=True)
            v2 = self.join_datetime(dt, time_stop, day_limit=True)

            v1 = v1.strftime("%Y-%m-%d %H:%M:%S")
            v2 = v2.strftime("%Y-%m-%d %H:%M:%S")

            domain = self._overlapped_domain(
                "date_start", "date_stop", v1, v2, inverse=False
            )
            domains.append(domain)

        state_domain = (
            [("state", "in", ["requested", "confirmed"])]
            if not_confirmed
            else [("state", "=", "confirmed")]
        )

        reservation_domain = AND(
            [
                [
                    ("active", "=", True),
                    ("validate", "=", True),
                ],
                state_domain,
                OR(domains),
            ]
        )
        reservation_obj = self.env["facility.reservation"]
        reservation_set = reservation_obj.search(reservation_domain)

        return reservation_set

    # =============================================================================
    # Context and extension hooks
    # =============================================================================

    def as_context_default(self):
        """Builds a dictionary that allows to pass by context the values have
        been set for the scheduler attributes. This dictionary will be used to
        open over and over again the assistant to search for free classrooms.

        Returns:
            dict: dictionary that allows to pass by context the attributes
        """

        self.ensure_one()

        return {
            "default_date_base": self.date_base.strftime("%Y-%m-%d"),
            "default_tz": self.tz,
            "default_time_start": self.time_start,
            "default_time_stop": self.time_stop,
            "default_full_day": self.full_day,
            "default_repeat": self.repeat,
            "default_interval_number": self.interval_number,
            "default_interval_type": self.interval_type,
            "default_weekday_ids": self.weekday_ids.mapped("id"),
            "default_month_type": self.month_type,
            "default_finish_type": self.finish_type,
            "default_finish_date": self.finish_date.strftime("%Y-%m-%d"),
            "default_finish_number": self.finish_number,
        }

    @staticmethod
    def _warn(message, title="Value error"):
        return {"warning": {"title": title, "message": message}}

    def _in_time_range(self, which="both"):
        """This method should be overridden by derived classes that need to
        check that ``date_base`` and ``finish_date`` field values are
        within the required bounds.

        Args:
            which (str, optional): left to check only date_base, right to check
            only finish_date or both to check both dates.

        Returns:
            bool: True if ``date_base`` and ``finish_date`` field values are
        within the required bounds, False otherwise.
        """

        return True

    # =============================================================================
    # Date and time utilities
    # =============================================================================

    @staticmethod
    def _max_day_time(microseconds=False):
        ms = 999999 if microseconds else 0
        d = date.min
        t = time(hour=23, minute=59, second=59, microsecond=ms)
        dt = datetime.min  # noqa: DTZ901

        return (datetime.combine(d, t) - dt).total_seconds() / 3600

    # Developing a function to round to a múltiple from math import ceil, floor
    @staticmethod
    def round_m(number, multiple, direction="nearest"):
        if direction == "up":
            return multiple * ceil(number / multiple)
        elif direction == "down":
            return multiple * floor(number / multiple)
        else:
            return multiple * round(number / multiple)

    def _field_changed(self, field_name):
        return self.env.context.get(field_name, False)

    @staticmethod
    def _float_interval(date_start, date_stop, natural=True):
        difference = date_stop - date_start
        difference = difference.total_seconds()

        if natural:
            value = max(difference, 0)

        return value / 3600.0

    @staticmethod
    def _date_addition(dt, hours):
        """Sum the given time, in hours, to the given datetime value.

        Args:
            dt (datetime): base date/time value or date value instead
            hours (float): time offset given in hours
        """

        if type(dt) is date:
            dt = datetime.combine(dt, time.min)

        return dt + timedelta(hours=hours)

    # -- Reservation interval ---------------------------------------------------

    def compute_interval(self, dt):
        """Rreturns the combination of the given date with the ``time_start``
        and with the ``time_stop`` field values.

        IMPORTANT: This method keep in mind ``full_day`` could be set to True.

        Args:
            dt (datetime): date or datetime to combine

        Returns:
            tuple: (date_start, date_stop) combined datetimes
        """

        self.ensure_one()

        time_start = 0.0 if self.full_day else self.time_start
        time_stop = 24.0 if self.full_day else self.time_stop
        date_start = self.join_datetime(dt, time_start, day_limit=True)
        date_stop = self.join_datetime(dt, time_stop, day_limit=True)

        return date_start, date_stop
