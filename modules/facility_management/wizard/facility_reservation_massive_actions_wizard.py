###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _

from logging import getLogger
from datetime import datetime

_logger = getLogger(__name__)


class FacilityReservationMassiveActionsWizard(models.TransientModel):
    """ Allo user to perform a choosen action over multiple facility
    reservation records.
    """

    _name = 'facility.reservation.massive.actions.wizard'
    _description = u'Facility reservation massive actions wizard'

    _rec_name = 'id'
    _order = 'id DESC'

    reservation_ids = fields.Many2many(
        string='Reservations',
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.default_reservation_ids(),
        help='Chosen reservations',
        comodel_name='facility.reservation',
        relation='facility_reservation_massive_action_wizard_reservation_rel',
        column1='wizard_id',
        column2='reservation_id',
        domain=[],
        context={},
    )

    def default_reservation_ids(self):
        expected = ('facility.reservation')
        reservation_set = self._get_active_records(self.env, expected=expected)
        return [(6, 0, reservation_set.ids)] if reservation_set else [(5,)]

    @api.onchange('reservation_ids')
    def _onchange_reservation_ids(self):

        if self.reservation_ids:

            state_list = self.reservation_ids.mapped('state')
            self.state = self._single_or_default(state_list)

            validate_list = self.reservation_ids.mapped('validate')
            self.validate = self._single_or_default(validate_list)

    reservation_count = fields.Integer(
        string='Reservation count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Number of chosen reservations',
        compute='_compute_reservation_count'
    )

    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        for record in self:
            record.reservation_count = len(record.reservation_ids)

    target_reservation_ids = fields.Many2many(
        string='Target reservations',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Reservations will be affected by chosen action',
        comodel_name='facility.reservation',
        relation='facility_reservation_massive_action_wizard_targets_rel',
        column1='wizard_id',
        column2='reservation_id',
        domain=[],
        context={},
        compute='_compute_target_reservation_ids'
    )

    @api.depends('action', 'reservation_ids')
    def _compute_target_reservation_ids(self):
        for record in self:
            if record.action == 'update':
                record._compute_target_reservation_ids_update()
            elif record.action == 'unbind':
                record._compute_target_reservation_ids_unbind()
            else:
                record.target_reservation_ids = [(5, None, None)]

    def _compute_target_reservation_ids_update(self):
        reservation_ids = self.reservation_ids.ids

        if reservation_ids:
            self.target_reservation_ids = [(6, None, reservation_ids)]
        else:
            self.target_reservation_ids = [(5, None, None)]

    def _compute_target_reservation_ids_unbind(self):
        reservation_set = self.reservation_ids.filtered(
            lambda r: r.scheduler_id)

        reservation_ids = reservation_set.ids

        if reservation_ids:
            self.target_reservation_ids = [(6, None, reservation_ids)]
        else:
            self.target_reservation_ids = [(5, None, None)]

    target_reservation_count = fields.Integer(
        string='Target count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Number of chosen reservations',
        compute='_compute_target_reservation_count'
    )

    @api.depends('target_reservation_ids')
    def _compute_target_reservation_count(self):
        for record in self:
            record.target_reservation_count = \
                len(record.target_reservation_ids)

    action = fields.Selection(
        string='Action',
        required=True,
        readonly=False,
        index=False,
        default='update',
        help='Action will be performed over chosen reservation records',
        selection='_dynamic_action_selection'
    )

    def _dynamic_action_selection(self):
        return [
            ('update', _('Update values')),
            ('unbind', _('Unbind from scheduler'))
        ]

    update_state = fields.Boolean(
        string='Update state',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help='Check it to update state'
    )

    state = fields.Selection(
        string='State',
        required=False,
        readonly=False,
        index=True,
        default='confirmed',
        help='Current reservation status',
        selection=[
            ('requested', 'Requested'),
            ('confirmed', 'Confirmed'),
            ('rejected', 'Rejected')
        ]
    )

    update_validate = fields.Boolean(
        string='Update validate',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help='Check it to update validate'
    )

    validate = fields.Boolean(
        string='Validate',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='If checked, the event date range will be checked before saving'
    )

    update_date_start = fields.Boolean(
        string='Update date start',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help='Checkit to update start date/time'
    )

    date_start = fields.Datetime(
        string='Beginning',
        required=False,
        readonly=False,
        index=True,
        default=lambda self: self.default_date_start(),
        help='Date/time of reservation start'
    )

    def default_date_start(self):
        return self._now_o_clock(round_up=True)

    update_date_stop = fields.Boolean(
        string='Update date stop',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help='Checkit to update stop date/time'
    )

    date_stop = fields.Datetime(
        string='Ending',
        required=False,
        readonly=False,
        index=True,
        default=lambda self: self.default_date_stop(),
        help='Date/time of reservation end'
    )

    def default_date_stop(self):
        return self._now_o_clock(offset_hours=1, round_up=True)

    tracking_disable = fields.Boolean(
        string='Tracking disable',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='Disable tracking'
    )

    def perform_action(self):
        tracking_disable_ctx = self.env.context.copy()
        tracking_disable_ctx.update({'tracking_disable': True})

        for record in self:
            if record.tracking_disable:
                record = record.with_context(tracking_disable_ctx)

            method_name = 'perform_action_{}'.format(record.action)
            method = getattr(record, method_name, False)

            if method:
                method()
            else:
                message = _('Unknown wizard action')
                raise ValueError(message)

    def _serialize_update_values(self):
        self.ensure_one()

        updatable = ['state', 'validate', 'date_start', 'date_stop']

        values = {}
        for field in updatable:
            update_field = f'update_{field}'
            if getattr(self, update_field, False):
                value = getattr(self, field, None)
                if isinstance(value, datetime):
                    value = fields.Datetime.to_string(value)

                values[field] = value

        return values

    def perform_action_update(self):

        for record in self:
            if not record.target_reservation_ids:
                continue

            values = record._serialize_update_values()
            if values:
                record.target_reservation_ids.write(values)

    def perform_action_unbind(self):
        for record in self:
            if not record.target_reservation_ids:
                continue

            record.target_reservation_ids.unbind()

    @api.model
    def _get_active_records(self, expected=None):
        """
        Retrieves active records based on the active model and IDs from the
        provided Odoo environment context.

        Args:
            expected (tuple): List of expected model names. It also supports 
                              either the name of the model itself or a set of 
                              records for that model as long as the model is 
                              unique.

        Returns:
            recordset or None: A recordset of active records based on the
            context's active model, or None if no active model found.
        """

        env = self.env
        _logger.debug(f'get_active_records({env}, {expected})')

        context = env.context
        active_model = context.get('active_model', False)

        if isinstance(expected, str):
            expected = [expected]
        elif isinstance(expected, models.Model):
            expected = [expected._name]

        if active_model and (expected is None or active_model in expected):
            record_set = env[active_model]

            active_ids = context.get('active_ids', [])

            if not active_ids:
                active_id = context.get('active_id', None)
                if active_id:
                    active_ids = [active_id]

            if active_ids:
                record_set = record_set.browse(active_ids)

        else:
            record_set = None

        _logger.debug(f'get_active_records > {record_set}')

        return record_set

    @staticmethod
    def _single_or_default(items, default=None):
        if (items and len(items) == 1 and items[0]):
            return items[0]
        else:
            return default

    @staticmethod
    def _now_o_clock(offset_hours=0, round_up=False):
        present = fields.datetime.now()
        oclock = present.replace(minute=0, second=0, microsecond=0)

        if round_up and (oclock < present):  # almost always
            oclock += timedelta(hours=1)

        return oclock + timedelta(hours=offset_hours)
