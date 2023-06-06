# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class IrActionsReport(models.Model):
    """ Method ``render_qweb_pdf`` was causing problems on line 796 when it
        trying to convert a ``None`` value to a python ``set`` in ``res_ids``.

        Here it is overwritten to prevent it.
    """

    _inherit = ['ir.actions.report']

    def _has_been_called_from_the_reporting_wizard(self):
        wizard_name = 'facility.reporting.wizard'
        active_model = self.env.context.get('active_model', False)
        return active_model == wizard_name

    def render_qweb_pdf(self, res_ids=None, data=None):
        if self._has_been_called_from_the_reporting_wizard():
            res_ids = res_ids or data['doc_ids']

        _super = super(IrActionsReport, self)
        return _super.render_qweb_pdf(res_ids, data)
