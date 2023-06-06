# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.osv.expression import TRUE_DOMAIN, FALSE_DOMAIN
from odoo.exceptions import UserError

from datetime import timedelta
from odoo.tools import safe_eval

from logging import getLogger


_logger = getLogger(__name__)


class FacilityReservation(models.Model):
    """ Facility reservation attributes
    """

    _name = 'facility.reservation'
    _description = u'Facility reservation'

    _inherit = [
        'ownership.mixin',
        'mail.thread'
    ]

    _rec_name = 'id'
    _order = 'date_start DESC, date_stop ASC'

    _check_company_auto = True

    name = fields.Char(
        string='Name',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='A short description to this reservation',
        size=50,
        translate=True,
        track_visibility='onchange'
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
        default=lambda self: self.default_state(),
        help='Current reservation status',
        selection=[
            ('requested', 'Requested'),
            ('confirmed', 'Confirmed'),
            ('rejected', 'Rejected')
        ],
        groups="facility_management.facility_group_monitor",
        track_visibility='onchange'
    )

    def default_state(self):
        return 'confirmed' if self._uid_is_technical() else 'requested'

    facility_id = fields.Many2one(
        string='Facility',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Facility to be reserved',
        comodel_name='facility.facility',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False,
        track_visibility='onchange'
    )

    complex_id = fields.Many2one(
        string='Complex',
        help='Complex to which the facility belongs',
        related='facility_id.complex_id',
        store=True
    )

    company_id = fields.Many2one(
        string='Company',
        related='facility_id.complex_id.company_id',
        store=True
    )

    type_id = fields.Many2one(
        string='Type',
        help='Type of the chosen facility',
        related='facility_id.type_id'
    )

    date_start = fields.Datetime(
        string='Beginning',
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.now_o_clock(round_up=True),
        help='Date/time of reservation start',
        track_visibility='onchange'
    )

    @api.onchange('date_start')
    def _onchange_date_start(self):
        self._compute_date_delay()

        return {
            'domain': {
                'facility_id': self._valid_facility_domain()
            }
        }

    date_stop = fields.Datetime(
        string='Ending',
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.now_o_clock(offset_hours=1, round_up=True),
        help='Date/time of reservation end',
        track_visibility='onchange'
    )

    @api.onchange('date_stop')
    def _onchange_date_stop(self):
        self._compute_date_delay()

        return {
            'domain': {
                'facility_id': self._valid_facility_domain()
            }
        }

    date_delay = fields.Float(
        string='Duration',
        required=True,
        readonly=False,
        index=False,
        default=0.0,
        digits=(16, 2),
        help='Time length of the reservation',
        store=False,
        compute='_compute_date_delay',
        search='_search_date_delay'
    )

    @api.depends('date_start', 'date_stop')
    def _compute_date_delay(self):
        for record in self:

            if record.date_start and record.date_stop:
                difference = (record.date_stop - record.date_start)
                value = max(difference.total_seconds(), 0)
            else:
                value = 0

            record.date_delay = value / 3600.0

    @api.onchange('date_delay')
    def _onchange_date_delay(self):
        for record in self:
            if record._origin.date_delay != record.date_delay:
                span = record.date_delay * 3600.0
                record.date_stop = record.date_start + timedelta(seconds=span)

    @api.model
    def _search_date_delay(self, operator, value):
        sql = '''
            SELECT
                "id" AS reservation_id
            FROM facility_reservation
            WHERE
                active AND
                (
                    EXTRACT(epoch FROM (date_stop - date_start)) / 3600.0
                ) {op} {val}
        '''

        sql = sql.format(op=operator, val=value)
        self.env.cr.execute(sql)

        rows = self.env.cr.dictfetchall()
        if not rows:
            domain = FALSE_DOMAIN
        else:
            reservation_ids = [row['reservation_id'] for row in (rows or [])]
            domain = [('id', 'in', reservation_ids)]

        return domain

    validate = fields.Boolean(
        string='Validate',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='If checked, the event date range will be checked before saving'
    )

    @api.onchange('validate')
    def _onchange_validate(self):
        return {
            'domain': {
                'facility_id': self._valid_facility_domain()
            }
        }

    scheduler_id = fields.Many2one(
        string='In scheduler',
        required=False,
        readonly=True,
        index=True,
        default=None,
        help='Scheduler to which the reservation belongs',
        comodel_name='facility.reservation.scheduler',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    color = fields.Integer(
        string='Color',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Color will be used in kanban view',
        compute="_compute_color"
    )

    @api.depends('state')
    def _compute_color(self):
        for record in self:
            if record.state == 'rejected':
                record.color = 1
            elif record.state == 'requested':
                record.color = 4
            else:
                if record.validate:
                    record.color = 10
                else:
                    record.color = 3

    _sql_constraints = [
        (
            'unique_facility_id',
            '''EXCLUDE USING gist (
                facility_id WITH =,
                tsrange ( date_start, date_stop ) WITH &&
            ) WHERE (
                validate AND state = 'confirmed'
            ); -- Requires btree_gist''',
            _('This facility is occupied by another reservation')
        ),
        (
            'positive_interval',
            'CHECK(date_start < date_stop)',
            _('Reservation cannot finish before it starts')
        ),
        (
            'minimum_name_length',
            '''CHECK(
                char_length(name) IS NULL OR
                char_length(name) < 1 OR
                char_length(name) >= 5
            )''',
            _('The minimum allowed name length is five characters')
        )
    ]

    def name_get(self):
        """ Only technicals can see the reservation owner. Other users see only
        facility name.

        Returns:
            tuple: ((id, name))
        """

        result = []

        uid_is_technical = self._uid_is_technical()

        for record in self:
            if record.name:
                name = record.name

            elif record.facility_id:
                facility = record.facility_id.name

                if uid_is_technical and record.owner_id:
                    owner = record.owner_id.name
                    name = '{} - {}'.format(facility, owner)
                else:
                    name = '{}'.format(facility)
            else:
                name = _('New facility')

            result.append((record.id, name))

        return result

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()

        _super = super(FacilityReservation, self)

        default = dict(default or {})

        default['date_start'] = self.date_start + timedelta(days=7)
        default['date_stop'] = self.date_stop + timedelta(days=7)

        return _super.copy(default=default)

    # @api.model
    # def _where_calc(self, domain, active_test=True):
    #     if not any(item[0] == 'state' for item in domain):
    #         domain = [('state', '=', 'confirmed')] + domain

    #     _super = super(FacilityReservation, self)
    #     return _super._where_calc(domain, active_test)

    @staticmethod
    def now_o_clock(offset_hours=0, round_up=False):
        present = fields.datetime.now()
        oclock = present.replace(minute=0, second=0, microsecond=0)

        if round_up and (oclock < present):  # almost always
            oclock += timedelta(hours=1)

        return oclock + timedelta(hours=offset_hours)

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

    def _valid_facility_domain(self):
        self.ensure_one()

        if self.validate:
            domain = FALSE_DOMAIN

            facility_obj = self.env['facility.facility']
            if self.date_start and self.date_stop:
                facility_set = facility_obj.available(
                    date_start=self.date_start, date_stop=self.date_stop)
                if facility_set:
                    facility_ids = facility_set.mapped('id')
                    domain = [('id', 'in', facility_ids)]
        else:
            domain = TRUE_DOMAIN

        return domain

    def _ensure_scheduler(self):
        self.ensure_one()

        mixin = self.env['facility.scheduler.mixin']

        if not self.scheduler_id:

            date_start = self.date_start.strftime('%Y-%m-%d %H:%M:%S')
            date_base, time_start = mixin.split_datetime(date_start)

            date_stop = self.date_stop.strftime('%Y-%m-%d %H:%M:%S')
            time_stop = mixin.split_datetime(date_stop)[1]

            scheduler_values = {
                'date_base': date_base,
                'time_start': time_start,
                'time_stop': time_stop,
                'name': self.name,
                'description': self.description,
                'active': self.active,
                'facility_id': self.facility_id.id,
                'confirm': self.state == 'confirmed',
                'validate': self.validate,
            }

            scheduler_obj = self.env['facility.reservation.scheduler']
            self.scheduler_id = scheduler_obj.create(scheduler_values)

        return self.scheduler_id

    def view_scheduler(self, force=False):
        self.ensure_one()

        if force and not self.scheduler_id:
            self._ensure_scheduler()

        if not self.scheduler_id:
            msg = _('This facility reservation has no associated scheduler')
            raise UserError(msg)

        xid = ('facility_management.'
               'action_facility_reservation_scheduler_as_wizard_act_window')
        action = self.env.ref(xid)

        ctx = self.env.context.copy()
        ctx.update(safe_eval(action.context))
        ctx.update({'default_facility_id': self.id})

        # Required to be called from facility_search_available_wizard button
        ctx.pop('tree_view_ref', False)

        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': 'facility.reservation.scheduler',
            'res_id': self.scheduler_id.id,
            'target': 'new',
            'name': action.name,
            'view_mode': 'form',
            'domain': [],
            'context': ctx,
            'search_view_id': action.search_view_id.id,
            'help': action.help,
            'flags': {'mode': 'readonly'}
        }

        return serialized

    # def date_delay_str(self, span=None):
    #     self.ensure_one()

    #     if span is None:
    #         span = (self.date_delay or 0)

    #     hours = int(span)
    #     pattern = '{h:02d} h'

    #     span = (span % 1)
    #     minutes = int(span * 60)
    #     if minutes:
    #         pattern += ' {m:02d}\''

    #     span = ((span * 60) % 1)
    #     seconds = int(span * 60)
    #     if seconds:
    #         pattern += ' {s:02d}\"'

    #     return pattern.format(h=hours, m=minutes, s=seconds)

