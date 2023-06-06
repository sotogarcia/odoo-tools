# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.osv.expression import TRUE_DOMAIN, FALSE_DOMAIN
from logging import getLogger

_logger = getLogger(__name__)


class FacilityReservationScheduler(models.Model):
    """ Group of reservations
    """

    _name = 'facility.reservation.scheduler'
    _description = u'Facility reservation scheduler'

    _inherit = ['ownership.mixin', 'facility.scheduler.mixin']

    _rec_name = 'id'
    _order = 'create_date DESC'

    name = fields.Char(
        string='Name',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='A short description to this reservation',
        size=50,
        translate=True
    )

    description = fields.Text(
        string='Description',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='A long description to this reservation',
        translate=True
    )

    active = fields.Boolean(
        string='Active',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='Enables/disables this reservation'
    )

    state = fields.Selection(
        string='State',
        required=True,
        readonly=False,
        index=True,
        default='schedule',
        help='Current group status',
        selection=[
            ('schedule', 'Schedule'),
            ('facility', 'Facility'),
            ('finish', 'Finish')
        ],
    )

    @api.onchange('state')
    def _onchange_state(self):
        if self.repeat and self.state != 'schedule' and \
           self.interval_type == 'week' and \
           not self._match_weekday(self.date_base):

            self.state = 'schedule'

            return self._warning(
                _('Wrong weekday'),
                _('The day of the week corresponding to the start date is not '
                  'among the selected days of the week')
            )

        if self.state == 'finish' and not self.facility_id:
            self.state = 'facility'

            return self._warning(
                _('Missing facility'),
                _('You must select a facility to make the reservation')
            )

        if self.state == 'facility':
            return {
                'domain': {
                    'facility_id': self._compute_facility_domain()
                }
            }

    @staticmethod
    def _warning(title, message):
        return {'warning': {'title': title, 'message': message}}

    facility_id = fields.Many2one(
        string='Facility',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Facility to be reserved',
        comodel_name='facility.facility',
        domain=None,
        context={},
        ondelete='cascade',
        auto_join=False
    )

    company_id = fields.Many2one(
        string='Company',
        related='facility_id.company_id',
        readonly=True
    )

    complex_id = fields.Many2one(
        string='Complex',
        help='Complex to which the facility belongs',
        related='facility_id.complex_id',
        readonly=True
    )

    type_id = fields.Many2one(
        string='Type',
        help='Type of facility',
        related='facility_id.type_id',
        readonly=True
    )

    users = fields.Integer(
        string='Users',
        help=_('Maximum number of students who can use this facility at the '
               'same time'),
        related='facility_id.users',
        readonly=True
    )

    confirm = fields.Boolean(
        string='Confirm',
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self.default_confirm(),
        help='If checked, the reservation will be confirmed'
    )

    def default_confirm(self):
        return self._uid_is_technical()

    validate = fields.Boolean(
        string='Validate',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='If checked, the event date range will be checked before saving'
    )

    reservation_ids = fields.One2many(
        string='Reservations',
        required=False,
        readonly=True,
        index=True,
        default=None,
        help='List with all the reservations created with this scheduler',
        comodel_name='facility.reservation',
        inverse_name='scheduler_id',
        domain=[],
        context={},
        auto_join=False,
        limit=None
    )

    reservation_count = fields.Integer(
        string='Reservation count',
        required=False,
        readonly=True,
        index=False,
        default=0,
        help='Number of reservations for this facility',
        compute='_compute_reservation_count',
        search='_search_reservation_count'
    )

    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        for record in self:
            record.reservation_count = len(record.reservation_ids)

    @api.model
    def _search_reservation_count(self, operator, value):
        domain = FALSE_DOMAIN

        if value is True:  # Field is mandatory
            domain = TRUE_DOMAIN if operator == '=' else FALSE_DOMAIN

        elif value is False:  # Field is mandatory
            domain = TRUE_DOMAIN if operator != '=' else FALSE_DOMAIN

        else:

            sql = self._search_reservation_count_sql

            self.env.cr.execute(sql.format(operator=operator, value=value))
            rows = self.env.cr.dictfetchall()

            if not rows:
                return FALSE_DOMAIN

            scheduler_ids = [row['scheduler_id'] for row in (rows or [])]

            domain = [('id', 'in', scheduler_ids)]

        return domain

    _search_reservation_count_sql = '''
        WITH active_reservations AS (
            SELECT
                "id" AS reservation_id,
                scheduler_id
            FROM
                facility_reservation
            WHERE
                active
                AND STATE = 'confirmed'
        )
         SELECT
            ars."id" AS scheduler_id
        FROM
            facility_reservation_scheduler AS ars
            LEFT JOIN active_reservations AS ar ON ars."id" = ar.scheduler_id
        WHERE
            ars.active
        GROUP BY
                ars."id"
        HAVING
            COUNT ( ar.facility_id ) {operator} {value}
    '''

    def _uid_is_technical(self):
        technical_group = 'facility_management.facility_group_monitor'

        result = False

        uid = self.env.context.get('uid', False)
        if uid:
            user_obj = self.env['res.users']
            user_set = user_obj.browse(uid)
            if user_set and user_set.has_group(technical_group):
                result = True

        return result

    def _compute_facility_domain(self, as_string=False):
        self.ensure_one()

        if self.validate:
            reservation_set = self.matching_reservations()

            domain = [('reservation_ids', '<>', reservation_set.mapped('id'))]

        else:
            domain = TRUE_DOMAIN

        return str(domain) if as_string else domain

    def make_reservations(self):

        reservation_obj = self.env['facility.reservation']

        for record in self:
            if record.repeat:
                dates = record._compute_repetition_dates()
            else:
                dates = [record.date_base]

            print(dates)

            default = {
                'name': record.name,
                'description': record.description,
                'active': True,
                'state': 'confirmed' if record.confirm else 'requested',
                'facility_id': record.facility_id.id,
                'date_start': None,
                'date_stop': None,
                'validate': record.validate,
                'owner_id': record.owner_id.id,
                'subrogate_id': record.subrogate_id.id,
                'scheduler_id': record.id
            }

            for dt in dates:

                date_start, date_stop = record.compute_interval(dt)

                values = default.copy()
                values.update({
                    'date_start': date_start,
                    'date_stop': date_stop
                })
                reservation_obj.create(values)
