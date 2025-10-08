# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools.safe_eval import safe_eval
from odoo.osv.expression import TRUE_DOMAIN, FALSE_DOMAIN
from ..utils.helpers import OPERATOR_MAP, one2many_count

from logging import getLogger
from odoo.tools.misc import format_date, format_time
import pytz
from datetime import datetime, date, time, timedelta


_logger = getLogger(__name__)


class FacilityReservationScheduler(models.Model):
    """Group of reservations"""

    _name = "facility.reservation.scheduler"
    _description = "Facility reservation scheduler"

    _inherit = ["ownership.mixin", "facility.scheduler.mixin"]

    _rec_name = "id"
    _order = "create_date DESC"

    name = fields.Char(
        string="Name",
        required=False,
        readonly=False,
        index=True,
        default=None,
        help="A short description for this reservation",
        size=255,
        translate=True,
    )

    description = fields.Text(
        string="Description",
        required=False,
        readonly=False,
        index=False,
        default=None,
        help="A long description for this reservation",
        translate=True,
    )

    active = fields.Boolean(
        string="Active",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="Enables/disables this reservation",
    )

    available_facility_ids = fields.Many2many(
        string="Available facilities",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help=(
            "Facilities available for the current date range. Used to "
            "filter 'facility_id' in the UI"
        ),
        comodel_name="facility.facility",
        relation="facility_reservation_scheduler_available_facility_rel",
        column1="scheduler_id",
        column2="facility_id",
        domain=[],
        context={},
        compute="_compute_available_facility_ids",
        compute_sudo=True,
        store=False,
    )

    @api.depends(
        "facility_id",
        "validate",
        "confirm",
        "date_base",
        "full_day",
        "time_start",
        "time_stop",
        "repeat",
        "interval_number",
        "finish_type",
        "finish_date",
        "finish_number",
        "interval_type",
        "weekday_ids",
        "month_type",
    )
    def _compute_available_facility_ids(self):
        """Compute dynamic set used to filter the facility selector."""
        facility_obj = self.env["facility.facility"]

        # One search([]) reused across all records when needed
        all_facilities = None

        for record in self:
            # Until the scheduler is both validated AND confirmed,
            # expose the full list to avoid confusing empty filters.
            if not (record.validate and record.confirm):
                if all_facilities is None:
                    all_facilities = facility_obj.search([])
                record.available_facility_ids = all_facilities
                continue

            # When validated+confirmed, apply the computed domain
            domain = record._compute_facility_domain(as_string=False)
            record.available_facility_ids = facility_obj.search(domain)

    @staticmethod
    def _warning(title, message):
        return {"warning": {"title": title, "message": message}}

    facility_id = fields.Many2one(
        string="Facility",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Facility to be reserved",
        comodel_name="facility.facility",
        domain=None,
        context={},
        ondelete="cascade",
        auto_join=False,
    )

    # all image fields are base64 encoded and PIL-supported
    image_1920 = fields.Image("Image", related="facility_id.image_1920")
    image_1024 = fields.Image("Image 1024", related="facility_id.image_1024")
    image_512 = fields.Image("Image 512", related="facility_id.image_512")
    image_256 = fields.Image("Image 256", related="facility_id.image_256")
    image_128 = fields.Image("Image 128", related="facility_id.image_128")

    company_id = fields.Many2one(
        string="Company", related="facility_id.company_id", readonly=True
    )

    complex_id = fields.Many2one(
        string="Complex",
        help="Complex the facility belongs to",
        related="facility_id.complex_id",
        readonly=True,
    )

    type_id = fields.Many2one(
        string="Type",
        help="Type of facility",
        related="facility_id.type_id",
        readonly=True,
    )

    users = fields.Integer(
        string="Users",
        help=(
            "Maximum number of students who can use this facility at the "
            "same time"
        ),
        related="facility_id.users",
        readonly=True,
    )

    confirm = fields.Boolean(
        string="Confirm",
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self.default_confirm(),
        help="If checked, the reservation will be confirmed",
    )

    def default_confirm(self):
        return self._uid_is_manager()

    validate = fields.Boolean(
        string="Validate",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="If checked, the event date range will be checked before saving",
    )

    reservation_ids = fields.One2many(
        string="Reservations",
        required=False,
        readonly=True,
        index=True,
        default=None,
        help="List with all the reservations created with this scheduler",
        comodel_name="facility.reservation",
        inverse_name="scheduler_id",
        domain=[],
        context={},
        auto_join=False,
    )

    reservation_count = fields.Integer(
        string="Reservation count",
        required=False,
        readonly=True,
        index=False,
        default=0,
        help="Number of reservations for this facility",
        compute="_compute_reservation_count",
        search="_search_reservation_count",
    )

    @api.depends("reservation_ids")
    def _compute_reservation_count(self):
        counts = one2many_count(self, "reservation_ids")

        for record in self:
            record.reservation_count = counts.get(record.id, 0)

    @api.model
    def _search_reservation_count(self, operator, value):
        # Handle boolean-like searches Odoo may pass for required fields
        if value is True:
            return TRUE_DOMAIN if operator == "=" else FALSE_DOMAIN
        if value is False:
            return TRUE_DOMAIN if operator != "=" else FALSE_DOMAIN

        cmp_func = OPERATOR_MAP.get(operator)
        if not cmp_func:
            return FALSE_DOMAIN  # unsupported operator

        counts = one2many_count(self.search([]), "reservation_ids")
        matched = [cid for cid, cnt in counts.items() if cmp_func(cnt, value)]

        return [("id", "in", matched)] if matched else FALSE_DOMAIN

    tracking_disable = fields.Boolean(
        string="Tracking disable",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="Disable the e-mail notification",
    )

    last_recalculated_at = fields.Char(
        string="Last update",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help=False,
        compute="_compute_last_recalculated_at",
    )

    @api.depends("write_date")
    def _compute_last_recalculated_at(self):
        for record in self:
            ts = record.write_date
            if not ts:
                record.last_recalculated_at = ""
                continue

            # Convert to user's timezone
            local_dt = fields.Datetime.context_timestamp(record, ts)
            today_local = fields.Date.context_today(record)

            if local_dt.date() == today_local:
                # Show only time if it is today
                record.last_recalculated_at = format_time(
                    self.env, local_dt.time()
                )
            else:
                # Show only date if it is another day
                record.last_recalculated_at = format_date(
                    self.env, local_dt.date()
                )

    def _uid_is_manager(self):
        technical_group = "facility_management.facility_group_manager"

        result = False

        uid = self.env.context.get("uid", False)
        if uid:
            user_obj = self.env["res.users"]
            user_set = user_obj.browse(uid)
            if user_set and user_set.has_group(technical_group):
                result = True

        return result

    def _compute_facility_domain(self, as_string=False):
        self.ensure_one()

        if self.validate:
            reservation_set = self.matching_reservations()

            domain = [("reservation_ids", "<>", reservation_set.mapped("id"))]

        else:
            domain = TRUE_DOMAIN

        return str(domain) if as_string else domain

    def _build_reservation_values(self):
        """Build a dictionary of reservation values based on the scheduler

        This method prepares the values needed to create or update a
        reservation record from the current scheduler record.

        Returns:
            dict: A dictionary of field values for a reservation.
        """

        self.ensure_one()

        return {
            "name": self.name,
            "description": self.description,
            # 'active': True,
            "state": "confirmed" if self.confirm else "requested",
            "facility_id": self.facility_id.id,
            "date_start": None,
            "date_stop": None,
            "validate": self.validate,
            "owner_id": self.owner_id.id,
            "subrogate_id": self.subrogate_id.id,
            "scheduler_id": self.id
            # ,'training_action_id': record.training_action_id.id
        }

    def _search_related_reservation(self):
        """Search for existing reservations related to this scheduler.

        Finds all reservation records that are linked to the current scheduler
        and applies the 'tracking_disable' context if it is set.

        Returns:
            recordset('facility.reservation'): The reservations associated with
            this scheduler.
        """

        self.ensure_one()

        reservation_set = self.env["facility.reservation"]

        if self:
            ids = self.ids

            domain = [
                "&",
                ("scheduler_id", "in", ids),
                "|",
                ("active", "=", True),
                ("active", "!=", True),
            ]

            reservation_set = reservation_set.search(
                domain, order="date_start ASC"
            )

        if self.tracking_disable:
            reservation_set = reservation_set.with_context(
                tracking_disable=True
            )

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
            lambda r: bool(r.active) != status
        )

        if target_set:
            if no_track:
                context = {"tracking_disable": True}
                reservation_set = reservation_set.with_context(context)

            values = {"active": bool(status)}
            target_set.write(values)

        return target_set

    @api.model_create_multi
    def create(self, value_list):
        """Overridden method 'create'"""

        parent = super(FacilityReservationScheduler, self)
        result = parent.create(value_list)

        result.make_reservations()

        return result

    def write(self, values):
        """Overridden method 'write'"""

        parent = super(FacilityReservationScheduler, self)
        result = parent.write(values)

        self.make_reservations()

        return result

    def _make_reservations(self):
        """Compute the intervals and either create new reservations or update
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
                reservation_set, False
            )

            index, length = 0, len(reservation_set)
            for dt in dates:
                date_start, date_stop = self.compute_interval(dt)
                values = defaults.copy()
                values.update(
                    {"date_start": date_start, "date_stop": date_stop}
                )

                if index < length:
                    reservation_set[index].write(values)
                    index = index + 1
                else:
                    reservation_set.create(values)

            if index < length:
                reservation_set[index:].unlink()

            self._toggle_reservation_status(changed_set.exists(), True)

            # Update write_date
            self._write({})

    def make_reservations(self, reload=True):
        """Create or update reservations from the current scheduler."""

        for record in self:
            record._make_reservations()

    def view_reservations(self):
        self.ensure_one()

        action_xid = "facility_management.action_reservations_act_window"
        act_wnd = self.env.ref(action_xid)

        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))
        context.update({"default_scheduler_id": self.id})

        domain = [("scheduler_id", "=", self.id)]

        serialized = {
            "type": "ir.actions.act_window",
            "res_model": act_wnd.res_model,
            "target": "current",
            "name": act_wnd.name,
            "view_mode": act_wnd.view_mode,
            "domain": domain,
            "context": context,
            "search_view_id": act_wnd.search_view_id.id,
            "help": act_wnd.help,
        }

        return serialized

    @api.depends("facility_id", "facility_id.name", "reservation_ids")
    @api.depends_context("lang")
    def _compute_display_name(self):
        for record in self:
            name = (
                record.name
                or (record.facility_id and record.facility_id.name)
                or _("New scheduler")
            )
            count = len(record.reservation_ids)

            record.display_name = _("%s (%s res.)") % (name, count)
