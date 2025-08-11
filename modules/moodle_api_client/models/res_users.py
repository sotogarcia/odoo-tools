# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class ResUsers(models.Model):

    _name = 'res.users'
    _inherit = 'res.users'

    moodle_user_id = fields.Integer(
        string='Moodle User ID',
        required=False,
        readonly=False,
        index=True,
        default=0,
        help='ID of the corresponding user in Moodle'
    )

    moodle_api_token = fields.Char(
        string='Moodle API token',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Authentication token to access the Moodle API as this user',
        translate=False
    )
