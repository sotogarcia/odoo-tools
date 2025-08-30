# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models
from logging import getLogger


_logger = getLogger(__name__)


class IrActionsReport(models.Model):
    """ Method ``render_qweb_pdf`` was causing problems on line 796 when it
        trying to convert a ``None`` value to a python ``set`` in ``res_ids``.

        Here it is overwritten to prevent it.

        NOTE (Odoo 18):
        ----------------
        In newer versions the canonical API is ``_render_qweb_pdf``.
        We override **both** ``render_qweb_pdf`` (for backward calls coming
        from other code) and ``_render_qweb_pdf`` (native in 14+), applying
        the same guard so ``res_ids`` is never ``None`` when called from
        our reporting wizard.
    """

    _inherit = ['ir.actions.report']

    def _has_been_called_from_the_reporting_wizard(self):
        wizard_name = 'facility.reporting.wizard'
        active_model = self.env.context.get('active_model', False)
        return active_model == wizard_name

    # ---- Odoo 14+ native entrypoint ---------------------------------------
    def _render_qweb_pdf(self, res_ids=None, data=None):
        if self._has_been_called_from_the_reporting_wizard():
            # Ensure a list, even if missing
            data = data or {}
            res_ids = res_ids or data.get('doc_ids') or []
        return super(IrActionsReport, self)._render_qweb_pdf(res_ids, data)

    # ---- Legacy entrypoint kept for compatibility -------------------------
    def render_qweb_pdf(self, res_ids=None, data=None):
        if self._has_been_called_from_the_reporting_wizard():
            data = data or {}
            res_ids = res_ids or data.get('doc_ids') or []
        return super(IrActionsReport, self).render_qweb_pdf(res_ids, data)
