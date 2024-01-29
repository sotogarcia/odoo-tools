# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _

from logging import getLogger


_logger = getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    ''' Module configuration attributes
    '''

    _inherit = ['res.config.settings']

    auto_archive_on_rejection = fields.Boolean(
        string='Auto archive',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help=('If enabled, records will be automatically archived when they '
              'are rejected'),
        config_parameter='facility_management.auto_archive_on_rejection'
    )
