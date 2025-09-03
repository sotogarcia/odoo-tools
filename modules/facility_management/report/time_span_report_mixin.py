# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _

from logging import getLogger
from datetime import timedelta, datetime
from pytz import timezone, utc

_logger = getLogger(__name__)


NOT_IMP_MSG = _('Abstract method «{}» not implemented in «{}» has been called')


class TimeSpanReportMixin(models.AbstractModel):
    """ Custom report behavior
    """

    _name = 'time.span.report.mixin'
    _description = u'Time span report mixin'

    def _read_record_values(self, record):
        msg = NOT_IMP_MSG.format('_read_record_values', self._name)
        raise NotImplementedError(msg)

    def _get_report_values(self, docids, data=None):
        msg = NOT_IMP_MSG.format('_get_report_values', self._name)
        raise NotImplementedError(msg)

    # -------------------------------------------------------------------------

    def _get_lang(self):
        lang = self.env.context.get('lang', False)
        if not lang:
            uid = self.env.context.get('uid', False)
            if uid:
                user = self.env['res.users'].browse(uid)
            else:
                user = self.env.ref('base.user_root').lang

            lang = user.lang if user else 'es_ES'

        return lang

    @classmethod
    def _date_range(cls, date_start, date_stop, full_weeks):
        """ Make a valid date range to loop by days.

        If ``full_weeks`` is True the range will start on the first day of the
        week and end on the last day of the week.

        Args:
            date_start (datetime): Description
            date_stop (datetime): Description
            full_weeks (bool): Description

        Returns:
            range: date range with one day increment
        """

        if full_weeks:
            date_start, date_stop = cls._weekly_interval(date_start, date_stop)

        days = (date_stop - date_start).days + 1

        return [date_start + timedelta(days=value) for value in range(0, days)]

    @api.model
    def _get_interval(self, data):
        """ Get date_start and date_stop value from given ``data['interval']``
            dictionary if have been set

            ```
            date_start = data['interval']['date_start']
            date_stop = data['interval']['date_stop']
            ```

        Args:
            data (dict): report data dictionary

        Returns:
            tuple: returns a ``(datetime, datetime)`` tuple
        """

        date_start, date_stop = None, None

        if data:
            interval = data.get('interval', False)

        if not interval:
            interval = self.env.context.get('time_span', False)

        if interval:

            date_start = interval.get('date_start', False)
            if isinstance(date_start, str):
                date_start = fields.Datetime.to_datetime(date_start)

            date_stop = interval.get('date_stop', False)
            if isinstance(date_stop, str):
                date_stop = fields.Datetime.to_datetime(date_stop)

        if not date_start:
            date_start = fields.Datetime.now()

        if not date_stop:
            date_stop = date_start

        return date_start, date_stop

    @staticmethod
    def _in(reservation, target_date):
        next_date = target_date + timedelta(days=1)

        begin = reservation.date_start >= target_date and \
            reservation.date_start < next_date
        finish = reservation.date_stop >= target_date and \
            reservation.date_stop < next_date

        return begin or finish

    @staticmethod
    def _week_day(target_date):
        return int(target_date.weekday())

    @classmethod
    def _week_str(cls, target_date):
        date_format = _('%B, %d')

        date_start = cls.midnight(target_date)
        date_stop = cls.midnight(target_date)

        offset = cls._week_day(date_start)
        date_start = date_start - timedelta(days=offset)
        date_stop = date_start + timedelta(days=6)

        date_start = date_start.strftime(date_format)
        date_stop = date_stop.strftime(date_format)

        return _('Week from {} to  {}').format(date_start, date_stop)

    @staticmethod
    def date_str(target_date):
        return target_date.strftime('%a, %d-%b').upper()

    @staticmethod
    def midnight(dt):
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    @api.model
    def time_str(self, reservation):
        tz_offset = self._get_timezone_offset(datetime.now())

        start = reservation.date_start + tz_offset
        stop = reservation.date_stop + tz_offset

        start = start.strftime('%H:%M')
        stop = stop.strftime('%H:%M')

        return '{}-{}'.format(start, stop)

    @classmethod
    def _weekly_interval(cls, date_start, date_stop):

        date_start = cls.midnight(date_start)
        date_stop = cls.midnight(date_stop)

        offset = cls._week_day(date_start)
        date_start = date_start - timedelta(days=offset)
        offset = cls._week_day(date_stop)
        date_stop = date_stop + timedelta(days=6 - offset)

        return date_start, date_stop

    @api.model
    def _get_timezone_offset(self, dt):
        tz = self.env.user.tz or utc.zone
        tz = timezone(tz)
        return tz.fromutc(dt).utcoffset()
