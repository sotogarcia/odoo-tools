# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class IrAttachment(models.Model):

    _name = 'ir.attachment'
    _inherit = 'ir.attachment'

    effective_url = fields.Char(
        string='Effective URL',
        required=False,
        readonly=True,
        index=False,
        default=None,
        help=('If the attachment is a URL, shows it; if it is a file, gives '
              'download URL'),
        translate=False,
        compute='_compute_effective_url'
    )

    @api.depends('type', 'url')
    def _compute_effective_url(self):
        for rec in self:
            if rec.type == 'url' and rec.url:
                rec.effective_url = rec.url
            elif rec.type == 'binary':
                rec.effective_url = f'/web/content/{rec.id}?download=true'
            else:
                rec.effective_url = ''
