# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.osv.expression import TRUE_DOMAIN, FALSE_DOMAIN
from odoo.tools import safe_eval

from logging import getLogger

_logger = getLogger(__name__)


class FacilityReservationScheduler(models.Model):
    """ Group of reservations
    """

    _name = 'facility.reservation.scheduler'
    _description = 'Facility reservation scheduler'

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
        size=255,
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
        return self._uid_is_manager()

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

    tracking_disable = fields.Boolean(
        string='Tracking disable',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='Disable the e-mail notification'
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
            COUNT ( ar.scheduler_id ) {operator} {value}
    '''

    def _uid_is_manager(self):
        technical_group = 'facility_management.facility_group_manager'

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

    def _build_reservation_values(self):
        """ Build a dictionary of reservation values based on the scheduler

        This method prepares the values needed to create or update a
        reservation record from the current scheduler record.

        Returns:
            dict: A dictionary of field values for a reservation.
        """

        self.ensure_one()

        return {
            'name': self.name,
            'description': self.description,
            # 'active': True,
            'state': 'confirmed' if self.confirm else 'requested',
            'facility_id': self.facility_id.id,
            'date_start': None,
            'date_stop': None,
            'validate': self.validate,
            'owner_id': self.owner_id.id,
            'subrogate_id': self.subrogate_id.id,
            'scheduler_id': self.id
            # ,'training_action_id': record.training_action_id.id
        }

    def _search_related_reservation(self):
        """ Search for existing reservations related to this scheduler.

        Finds all reservation records that are linked to the current scheduler
        and applies the 'tracking_disable' context if it is set.

        Returns:
            recordset('facility.reservation'): The reservations associated with
            this scheduler.
        """

        self.ensure_one()

        reservation_set = self.env['facility.reservation']

        if self:
            ids = self.ids

            domain = [
                '&',
                ('scheduler_id', 'in', ids),
                '|',
                ('active', '=', True),
                ('active', '!=', True)
            ]

            reservation_set = reservation_set.search(
                domain, order='date_start ASC')

        if self.tracking_disable:
            reservation_set = \
                reservation_set.with_context(tracking_disable=True)

        return reservation_set

    @staticmethod
    def _toggle_reservation_status(reservation_set, status, no_track=True):
        """Silently change the status of reservations.

        This method changes the status of reservations in the provided
        recordset to a specified new state. It is intended to be used both
        before and after performing bulk reservation changes.

        Args:
            reservation_set (recordset): Set of reservation records.
            status (bool): New activation status (True to activate, False
                           to deactivate).
            no_track (bool, optional): Indicates whether change tracking should
                                       be disabled (default is True).

        Returns:
            recordset: Set of records that were modified as a result of the
                       status change.
        """
        status = bool(status)

        target_set = reservation_set.filtered(
            lambda r: bool(r.active) != status)

        if target_set:
            if no_track:
                context = {'tracking_disable': True}
                reservation_set = reservation_set.with_context(context)

            values = {'active': bool(status)}
            target_set.write(values)

        return target_set

    def _make_reservations(self):
        """ Compute the intervals and either create new reservations or update
        existing ones accordingly. Excess reservations are unlinked.
        """

        self.ensure_one()

        if self.repeat:
            dates = self._compute_repetition_dates()
        else:
            dates = [self.date_base]

        defaults = self._build_reservation_values()

        reservation_set = self._search_related_reservation()

        with self.env.cr.savepoint():
            changed_set = self._toggle_reservation_status(
                reservation_set, False)

            index, length = 0, len(reservation_set)
            for dt in dates:

                date_start, date_stop = self.compute_interval(dt)
                values = defaults.copy()
                values.update({
                    'date_start': date_start,
                    'date_stop': date_stop
                })

                if index < length:
                    reservation_set[index].write(values)
                    index = index + 1
                else:
                    reservation_set.create(values)

            if index < length:
                reservation_set[index:].unlink()

            self._toggle_reservation_status(changed_set.exists(), True)

    def make_reservations(self):
        """ Create or update reservations from the current scheduler.
        """

        for record in self:
            record._make_reservations()

        return self._sertialize_reservation_act(target='main')

    def remove_reservations(self):
        removed_ids = []

        for record in self:
            today = fields.Date.context_today(record)
            today = fields.Date.to_string(today)

            reservation_set = record._search_related_reservation()
            if reservation_set:
                removed_ids.extend(reservation_set.ids)
                reservation_set.unlink()

        return self._sertialize_reservation_act(target='main')

    def _sertialize_reservation_act(self, target=None):
        action_xid = 'facility_management.action_reservations_act_window'
        act_wnd = self.env.ref(action_xid)

        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))

        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': act_wnd.res_model,
            'target': target or act_wnd.target,
            'name': act_wnd.name,
            'view_mode': act_wnd.view_mode,
            'domain': safe_eval(act_wnd.domain),
            'context': context,
            'search_view_id': act_wnd.search_view_id.id,
            'help': act_wnd.help
        }

        return serialized
