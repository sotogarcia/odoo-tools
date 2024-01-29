# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from logging import getLogger
from odoo.osv.expression import TERM_OPERATORS_NEGATION
from odoo.osv.expression import TRUE_DOMAIN, FALSE_DOMAIN


_logger = getLogger(__name__)


class IrExports(models.Model):
    """ Allow to view and export ir.exports records
    """

    _name = 'ir.exports'
    _inherit = 'ir.exports'

    export_fields_count = fields.Integer(
        string='Field count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Number of fields in export record',
        compute='_compute_export_fields_count',
        search='_search_export_fields_count'
    )

    @api.depends('export_fields')
    def _compute_export_fields_count(self):
        for record in self:
            record.export_fields_count = len(record.export_fields)

    @api.model
    def _search_export_fields_count(self, operator, value):
        sql = '''
            SELECT
                ie."id" AS export_id
            FROM
                ir_exports AS ie
                LEFT JOIN ir_exports_line AS iel ON iel.export_id = ie."id"
            GROUP BY
                ie."id"
            HAVING COUNT ( iel."id" )::INTEGER {op} {value}
        '''

        if isinstance(value, bool):
            if value is False:
                operator = TERM_OPERATORS_NEGATION[operator]
                value = not value

            if operator == '=':  # is set
                domain = TRUE_DOMAIN
            else:  # is not set
                domain = FALSE_DOMAIN

        else:
            cursor = self.env.cr
            cursor.execute(sql.format(op=operator, value=value))
            rows = cursor.dictfetchall()
            ids = [v for k, v in rows.items()]
            domain = [('id', 'in', ids)]

        return domain
