# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class MoodleApiClientCalendarEvent(models.Model):
    _name = 'moodle.api.client.calendar.event'
    _description = u'Moodle api client calendar event'

    _rec_name = 'name'
    _order = 'start DESC, name ASC'

    _inherit = ['moodle.api.client.base']

    start = fields.Datetime(
        string='Start Time',
        required=True,
        readonly=False,
        index=True,
        default=fields.Datetime.now,
        help='Start date and time of the event'
    )

    duration = fields.Float(
        string='Duration (hours)',
        required=False,
        readonly=False,
        index=False,
        default=0.0,
        help='Duration of the event in hours'
    )

    user_id = fields.Many2one(
        string='Author',
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self._default_user_id(),
        help='User who created the event',
        comodel_name='res.users',
        ondelete='cascade'
    )

    def _default_user_id(self):
        try:
            return self.env.user.id or self.env.ref('base.user_root').id
        except Exception:
            return 1

    moodle_user_id = fields.Integer(
        string='Moodle User ID',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='ID of the corresponding user in Moodle',
        related="user_id.moodle_user_id"
    )

    # -------------------------------------------------------------------------
    # MOODLE CRUD METHODS
    # -------------------------------------------------------------------------

    def moodle_read(self):
        for record in self:
            record._moodle_read()

    def _moodle_read(self):
        """Retrieve this calendar event from Moodle by its ID"""
        self.ensure_one()

        return self.platform_id._get_driver().call(
            'core_calendar_get_calendar_event_by_id',
            {'eventid': self.moodleid}
        )

    def moodle_create(self):
        for record in self:
            record._moodle_create()

    def _moodle_create(self):
        """Create a new calendar event in Moodle"""
        self.ensure_one()

        params = {
            'events[0][name]': self.name,
            'events[0][description]': self.description or '',
            'events[0][timestart]': int(fields.Datetime.from_string(self.start).timestamp()),
            'events[0][duration]': int(self.duration * 3600),
            'events[0][userid]': self.moodle_user_id,
            'events[0][eventtype]': 'user',
        }

        return self.platform_id._get_driver().call(
            'core_calendar_create_calendar_events',
            params
        )

    def moodle_write(self):
        for record in self:
            record._moodle_write()

    def _moodle_write(self):
        """Update this calendar event in Moodle"""
        self.ensure_one()

        params = {
            'events[0][id]': self.moodleid,
            'events[0][name]': self.name,
            'events[0][description]': self.description or '',
            'events[0][timestart]': int(fields.Datetime.from_string(self.start).timestamp()),
            'events[0][duration]': int(self.duration * 3600)
        }

        return self.platform_id._get_driver().call(
            'core_calendar_submit_create_update_form',
            params
        )

    def moodle_unlink(self):
        for record in self:
            record._moodle_unlink()

    def _moodle_unlink(self):
        """Delete this calendar event in Moodle"""
        self.ensure_one()

        return self.platform_id._get_driver().call(
            'core_calendar_delete_calendar_events',
            {'events[0][eventid]': self.moodleid}
        )
