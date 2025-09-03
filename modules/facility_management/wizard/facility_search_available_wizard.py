# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.osv.expression import AND
from odoo.tools.safe_eval import safe_eval

from logging import getLogger


_logger = getLogger(__name__)


class FacilitySearchAvailableWizard(models.TransientModel):

    _name = 'facility.search.available.wizard'
    _description = u'Facility search available wizard'

    _inherit = ['facility.scheduler.mixin']

    _rec_name = 'id'
    _order = 'id DESC'

    type_ids = fields.Many2many(
        string='Types',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Adding types will restrict the results to matching ones',
        comodel_name='facility.type',
        relation='facility_search_available_wizard_type_rel',
        column1='wizard_id',
        column2='type_id',
        domain=[],
        context={},
    )

    exclude_types = fields.Boolean(
        string='Exclude types',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help='Check to exclude chosen types'
    )

    complex_ids = fields.Many2many(
        string='Complexes',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Adding complexes will restrict the results to matching ones',
        comodel_name='facility.complex',
        relation='facility_search_available_wizard_complex_rel',
        column1='wizard_id',
        column2='complex_id',
        domain=[],
        context={},
    )

    exclude_complexes = fields.Boolean(
        string='Exclude complexes',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help='Check to exclude chosen complexes'
    )

    @staticmethod
    def _real_id(record_set, single=False):
        """ Return a list with no NewId's of a single no NewId
        """

        result = []

        if record_set and single:
            record_set.ensure_one()

        for record in record_set:
            if isinstance(record.id, models.NewId):
                result.append(record._origin.id)
            else:
                result.append(record.id)

        if single:
            result = result[0] if len(result) == 1 else None

        return result

    def as_context_default(self):
        parent = super(FacilitySearchAvailableWizard, self)

        if self.type_ids:
            type_ops = [(6, 0, self.type_ids.mapped('id'))]
        else:
            type_ops = [(5, 0, 0)]

        if self.complex_ids:
            complex_ops = [(6, 0, self.complex_ids.mapped('id'))]
        else:
            complex_ops = [(5, 0, 0)]

        ctx = parent.as_context_default()
        ctx.update({
            'default_type_ids': type_ops,
            'default_complex_ids': complex_ops,
            'default_exclude_types': self.exclude_types,
            'default_exclude_complexes': self.exclude_complexes
        })

        return ctx

    def _search_for_facilities(self):
        domains = []

        reservation_set = self.matching_reservations()
        if reservation_set:
            reservation_ids = reservation_set.mapped('id')
            not_reserved = [('reservation_ids', '<>', reservation_ids)]
            domains.append(not_reserved)

        if self.type_ids:
            type_ids = self._real_id(self.type_ids)
            type_op = 'not in' if self.exclude_types else 'in'
            type_domain = [('type_id', type_op, type_ids)]
            domains.append(type_domain)

        if self.complex_ids:
            complex_ids = self._real_id(self.complex_ids)
            complex_op = 'not in' if self.exclude_complexes else 'in'
            complex_domain = [('complex_id', complex_op, complex_ids)]
            domains.append(complex_domain)

        facility_domain = AND(domains)
        facility_obj = self.env['facility.facility']
        facility_set = facility_obj.search(facility_domain)

        return facility_set

    def view_facilities(self):
        self.ensure_one()

        action_xid = ('facility_management.'
                      'action_facilities_act_window')
        action = self.env.ref(action_xid)

        ctx = self.env.context.copy()
        ctx.update(safe_eval(action.context))
        ctx.update(self.as_context_default())

        facility_set = self._search_for_facilities()

        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': 'facility.facility',
            'target': 'main',
            'name': _('Facilities that match the criteria'),
            'view_mode': action.view_mode,
            'domain': [('id', 'in', facility_set.mapped('id'))],
            'context': ctx,
            'search_view_id': action.search_view_id.id,
            'help': action.help
        }

        return serialized
