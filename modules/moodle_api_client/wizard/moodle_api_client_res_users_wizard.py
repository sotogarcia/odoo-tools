# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class MoodleApiClientResUsersWizard(models.TransientModel):

    _name = 'moodle.api.client.res.users.wizard'
    _description = u'Moodle api client res users wizard'

    _rec_name = 'id'
    _order = 'id DESC'

    user_id = fields.Many2one(
        string='User',
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.default_user_id(),
        help='User whose Moodle credentials will be consulted or updated',
        comodel_name='res.users',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    def default_user_id(self):
        err = _('You must choose a single user before launching this wizard')

        context = self.env.context
        active_model = context.get('active_model')
        active_id = context.get('active_id')

        if active_model != 'res.users' or not active_id:
            raise ValidationError(err)

        user = self.env[active_model].browse(active_id)
        if not user.exists():
            raise ValidationError(err)

        return user

    @api.onchange('user_id')
    def _onchange_user_id(self):
        self.moodle_user_id = self.user_id.moodle_user_id
        self.moodle_api_token = self.user_id.moodle_api_token

    moodle_user_id = fields.Integer(
        string='Moodle User ID',
        required=True,
        readonly=False,
        index=True,
        default=0,
        help='ID of the corresponding user in Moodle'
    )

    moodle_api_token = fields.Char(
        string='Moodle API token',
        required=True,
        readonly=False,
        index=False,
        default=None,
        help='Authentication token to access the Moodle API as this user',
        translate=False
    )

    _sql_constraints = [
        (
            'positive_moodle_user_id',
            'CHECK(moodle_user_id > 0)',
            _(u'The Moodle User ID must be a positive integer.')
        )
    ]

    def perform_action(self):
        for record in self:
            record._perform_action()

    def _perform_action(self):
        self.ensure_one()

        self.user_id.write({
            'moodle_user_id': self.moodle_user_id,
            'moodle_api_token': self.moodle_api_token
        })
