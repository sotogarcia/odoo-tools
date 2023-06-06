# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools import safe_eval
from odoo.osv.expression import TRUE_DOMAIN, FALSE_DOMAIN
from odoo.exceptions import ValidationError

from logging import getLogger
from math import trunc, pow
from random import random
from re import sub

_logger = getLogger(__name__)


class FacilityComplex(models.Model):
    """ A group of facilities, usually in the same location address
    """

    _name = 'facility.complex'
    _description = u'Facility complex'

    _rec_name = 'name'
    _order = 'name ASC'

    _inherit = [
        'image.mixin',
        'mail.thread',
        'ownership.mixin'
    ]

    _inherits = {'res.partner': 'partner_id'}

    _check_company_auto = True

    partner_id = fields.Many2one(
        string='Partner',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Contact information',
        comodel_name='res.partner',
        domain=[],
        context={},
        ondelete='restrict',
        auto_join=False
    )

    # Overwritten field
    company_id = fields.Many2one(
        string='Company',
        required=True,
        readonly=True,
        index=True,
        default=lambda self: self.env.company,
        help='The company this record belongs to',
        comodel_name='res.company',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    code = fields.Char(
        string='Internal code',
        required=True,
        readonly=False,
        index=False,
        default=None,
        help='Enter new internal code',
        size=30,
        translate=False
    )

    description = fields.Text(
        string='Description',
        help='Enter new description',
        related='partner_id.comment'
    )

    facility_ids = fields.One2many(
        string='Facilities',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='Facilities in this complex',
        comodel_name='facility.facility',
        inverse_name='complex_id',
        domain=[],
        context={},
        auto_join=False,
        limit=None
    )

    facility_count = fields.Integer(
        string='Facility count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Number of facilities in this complex',
        compute='_compute_facility_count',
        search='_search_facility_count'
    )

    @api.depends('facility_ids')
    def _compute_facility_count(self):
        for record in self:
            record.facility_count = len(record.facility_ids)

    @api.model
    def _search_facility_count(self, operator, value):
        domain = FALSE_DOMAIN

        if value is True:  # Field is mandatory
            domain = TRUE_DOMAIN if operator == '=' else FALSE_DOMAIN

        elif value is False:  # Field is mandatory
            domain = TRUE_DOMAIN if operator != '=' else FALSE_DOMAIN

        else:

            sql = self._search_facility_count_sql

            self.env.cr.execute(sql.format(operator=operator, value=value))
            rows = self.env.cr.dictfetchall()

            if not rows:
                return FALSE_DOMAIN

            facility_ids = [row['complex_id'] for row in (rows or [])]

            domain = [('id', 'in', facility_ids)]

        return domain

    _search_facility_count_sql = '''
        WITH active_facilities AS (
            SELECT
                "id" AS facility_id,
                complex_id
            FROM
                facility
            WHERE
                active
        )
        SELECT
            aec."id" AS complex_id
        FROM
            complex AS aec
            LEFT JOIN active_facilities AS af ON aec."id" = af.complex_id
        WHERE
            aec.active
        GROUP BY
            aec."id"
        HAVING
            COUNT ( af.complex_id ) {operator} {value}
    '''

    _sql_constraints = [
        (
            'unique_partner_id',
            'UNIQUE("partner_id")',
            _('A complex with the same data already exists')
        ),
        (
            'unique_complex_code',
            'UNIQUE("code")',
            _('A complex with that code already exists')
        )
    ]

    @api.constrains('partner_id')
    def _check_unique_name_by_company(self):
        msg_1 = _('Complex must have a name')
        msg_2 = _('There is already a complex with the same name '
                  'in this company')

        for record in self:
            partner = record.partner_id
            if not partner or not partner.name or len(partner.name) < 1:
                raise ValidationError(msg_1)
            else:
                res_id = record.id if isinstance(record.id, int) else 0
                complex_domain = [
                    '&',
                    ('id', '!=', res_id),
                    ('name', 'ilike', partner.name)
                ]
                complex_obj = self.env['facility.complex']
                complex_set = complex_obj.search(complex_domain, limit=1)

                if complex_set:
                    raise ValidationError(msg_2)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})

        rand = str(trunc(random() * pow(10, 15))).zfill(15)
        cursor = self.env.cr

        sql = '''
            WITH complex_name AS (
                SELECT
                    fc."id",
                    rp."name",
                    fc."code"
                FROM
                    facility_complex AS fc
                    INNER JOIN res_partner AS rp ON rp."id" = fc.partner_id
                WHERE TRUE {where}
            )
            SELECT
                ( '{part}' || gs )::VARCHAR AS "value"
            FROM
                generate_series ( 1, 999999, 1 ) AS gs
            LEFT JOIN complex_name AS cn
                ON cn."{field}" = ( '{part}' || gs )
            WHERE
                cn."id" IS NULL
                LIMIT 1;
        '''

        code = sub('[0-9]+$', '', self.code)
        cursor.execute(sql.format(where='', part=code, field='code'))
        row = cursor.dictfetchone()
        if not row or len(row['value']) > 30:
            code = rand
        else:
            code = row['value']

        name = sub('[0-9]$', '', self.name)
        where = 'AND fc.company_id = {}'.format(self.env.company.id)
        cursor.execute(sql.format(where=where, part=name, field='name'))
        row = cursor.dictfetchone()
        name = rand if not row else row['value']

        default.update({'name': name, 'code': code})

        return super(FacilityComplex, self).copy(default)

    @api.model
    def default_get(self, fields):
        parent = super(FacilityComplex, self)
        values = parent. default_get(fields)

        company = self.env.company or self.env.ref('base.main_company')
        values['company_id'] = company.id
        values['employee'] = False
        values['type'] = 'other'
        values['is_company'] = False
        # values['company_type'] = 'company'

        return values

    def view_facilities(self):
        self.ensure_one()

        action_xid = ('facility_management.'
                      'action_facilities_act_window')
        action = self.env.ref(action_xid)

        ctx = self.env.context.copy()
        ctx.update(safe_eval(action.context))
        ctx.update({'default_complex_id': self.id})

        domain = [('complex_id', '=', self.id)]

        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': 'facility.facility',
            'target': 'current',
            'name': action.name,
            'view_mode': action.view_mode,
            'domain': domain,
            'context': ctx,
            'search_view_id': action.search_view_id.id,
            'help': action.help
        }

        return serialized
