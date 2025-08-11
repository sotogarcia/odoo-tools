# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _

from logging import getLogger


_logger = getLogger(__name__)


class MoodleApiClientBase(models.AbstractModel):

    _name = 'moodle.api.client.base'
    _description = u'Moodle api client base'

    platform_id = fields.Many2one(
        string='Platform',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Moodle platform configuration used for this object',
        comodel_name='moodle.api.client.platform',
        ondelete='restrict'
    )

    # - Field: user_id (default)
    # ------------------------------------------------------------------------

    user_id = fields.Many2one(
        string='Author',
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self._default_user_id(),
        help='User who created the forum',
        comodel_name='res.users',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    def _default_user_id(self):
        try:
            return self.env.user.id or self.env.ref('base.user_root').id
        except Exception:
            return 1  # fallback to superuser ID in case of unexpected errors
    # ------------------------------------------------------------------------

    moodleid = fields.Integer(
        string='Moodle ID',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='ID of the corresponding object in Moodle'
    )

    name = fields.Char(
        string='Name',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Name of the object in Odoo or Moodle',
        translate=False
    )

    description = fields.Text(
        string='Description',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Optional description of the object',
        translate=False
    )

    active = fields.Boolean(
        string='Active',
        required=False,
        readonly=False,
        index=True,
        default=True,
        help='Enable or disable this vacancy position without deleting it',
        track_visibility='onchange'
    )

    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        required=False,
        readonly=True,
        index=True,
        default=None,
        help='Date and time of last synchronization with Moodle'
    )

    last_sync_error = fields.Text(
        string='Last Sync Error',
        required=False,
        readonly=True,
        index=False,
        default=None,
        help='Last error message received from Moodle during synchronization',
        translate=False
    )

    def _get_driver_class(self, driver_name):
        if driver_name == 'moodle_03_04_03':
            from ..drivers.moodle_03_04_03 import MoodleDriver_03_04_03
            return MoodleDriver_03_04_03
        
        raise ValueError('Unsupported driver: %s' % driver_name)
