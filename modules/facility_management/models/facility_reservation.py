###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from datetime import date, datetime, time, timedelta

import pytz
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import (
    FALSE_DOMAIN,
    NEGATIVE_TERM_OPERATORS,
    TRUE_DOMAIN,
)
from odoo.tools import str2bool
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _


class FacilityReservation(models.Model):
    """Facility reservation attributes"""

    _name = "facility.reservation"
    _description = "Facility reservation"

    _inherit = ["ownership.mixin", "mail.thread"]  # noqa: RUF012

    _rec_name = "id"
    _order = "date_start ASC, date_stop ASC"

    _check_company_auto = True

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Name",
        required=False,
        readonly=False,
        index=True,
        default=None,
        help="A short description for this reservation",
        size=255,
        translate=True,
        tracking=True,
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
        tracking=True,
    )

    state = fields.Selection(
        string="State",
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.default_state(),
        help="Current reservation status",
        selection=[
            ("requested", "Requested"),
            ("confirmed", "Confirmed"),
            ("rejected", "Rejected"),
        ],
        groups="facility_management.facility_group_monitor",
        tracking=True,
    )

    facility_id = fields.Many2one(
        string="Facility",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Facility to be reserved",
        comodel_name="facility.facility",
        domain=[],
        context={},
        ondelete="cascade",
        auto_join=False,
        tracking=True,
    )

    complex_id = fields.Many2one(
        related="facility_id.complex_id",
        store=True,
        index=True,
    )

    company_id = fields.Many2one(
        related="facility_id.complex_id.company_id",
        store=True,
        index=True,
    )

    type_id = fields.Many2one(
        string="Type",
        help="Type of the chosen facility",
        related="facility_id.type_id",
    )

    date_start = fields.Datetime(
        string="Beginning",
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.now_o_clock(round_up=True),
        help="Date/time of reservation start",
        tracking=True,
    )

    date_stop = fields.Datetime(
        string="Ending",
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.now_o_clock(offset_hours=1, round_up=True),
        help="Date/time of reservation end",
        tracking=True,
    )

    date_delay = fields.Float(
        string="Duration",
        required=True,
        readonly=False,
        index=False,
        default=0.0,
        digits=(16, 2),
        help="Time length of the reservation",
        store=True,
        compute="_compute_date_delay",
        inverse="_inverse_date_delay",
    )

    validate = fields.Boolean(
        string="Validate",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="If checked, the event date range will be checked before saving",
    )

    scheduler_id = fields.Many2one(
        string="In scheduler",
        required=False,
        readonly=True,
        index=True,
        default=None,
        help="Scheduler to which the reservation belongs",
        comodel_name="facility.reservation.scheduler",
        domain=[],
        context={},
        ondelete="cascade",
        auto_join=False,
        copy=False,
    )

    has_scheduler = fields.Boolean(
        string="Has scheduler",
        required=False,
        readonly=True,
        index=False,
        default=False,
        help="Check this if the reservation has a related scheduler",
        compute="_compute_has_scheduler",
        search="_search_has_scheduler",
    )

    reservation_count = fields.Integer(
        string="Scheduler",
        related="scheduler_id.reservation_count",
    )

    color = fields.Integer(
        string="Color",
        required=True,
        readonly=True,
        index=False,
        default=0,
        help="Color will be used in kanban view",
        compute="_compute_color",
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
        relation="facility_reservation_available_facility_rel",
        column1="reservation_id",
        column2="facility_id",
        domain=[],
        context={},
        compute="_compute_available_facility_ids",
    )

    # -------------------------------------------------------------------------
    # SQL CONSTRAINTS
    # -------------------------------------------------------------------------

    _sql_constraints = [  # noqa: RUF012
        (
            "unique_facility_id",
            """EXCLUDE USING gist (
                facility_id gist_int4_ops WITH =,
                tsrange ( date_start, date_stop ) WITH &&
            ) WHERE (
                active
                AND validate
                AND state = 'confirmed'
            ); -- Requires btree_gist""",
            "This facility is occupied by another reservation",
        ),
        (
            "positive_interval",
            "CHECK(date_start < date_stop)",
            "Reservation cannot finish before it starts",
        ),
    ]

    # -------------------------------------------------------------------------
    # DEFAULT VALUES
    # -------------------------------------------------------------------------

    def default_state(self):
        return "confirmed" if self._uid_is_manager() else "requested"

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange("facility_id")
    def _onchange_facility_id(self):
        facility_complex = self.facility_id.complex_id

        if facility_complex and facility_complex.is_an_allowed_supervisor():
            self.state = "confirmed"
        else:
            self.state = "requested"

    @api.onchange("date_start")
    def _onchange_date_start(self):
        self._compute_date_delay()

    @api.onchange("date_stop")
    def _onchange_date_stop(self):
        self._compute_date_delay()

    @api.onchange("date_delay")
    def _onchange_date_delay(self):
        for record in self:
            if record._origin.date_delay != record.date_delay:
                span = record.date_delay * 3600.0
                record.date_stop = record.date_start + timedelta(seconds=span)

    # -------------------------------------------------------------------------
    # COMPUTE, INVERSE AND SEARCH METHODS
    # -------------------------------------------------------------------------

    @api.depends("date_start", "date_stop")
    def _compute_date_delay(self):
        for record in self:
            if record.date_start and record.date_stop:
                difference = record.date_stop - record.date_start
                value = max(difference.total_seconds(), 0)
            else:
                value = 0

            record.date_delay = value / 3600.0

    def _inverse_date_delay(self):
        for record in self:
            if record.date_start is not False:
                span = record.date_delay * 3600.0
                record.date_stop = record.date_start + timedelta(seconds=span)

    @api.depends("scheduler_id")
    def _compute_has_scheduler(self):
        for record in self:
            record.has_scheduler = bool(record.scheduler_id)

    @api.model
    def _search_has_scheduler(self, operator, value):
        if operator not in ("=", "!="):
            return FALSE_DOMAIN

        value = bool(value)

        if operator == "!=":
            value = not value

        if value:
            return [("scheduler_id", "!=", False)]

        return [("scheduler_id", "=", False)]

    @api.depends("state", "validate")
    def _compute_color(self):
        for record in self:
            if record.state == "rejected":
                record.color = 1
            elif record.state == "requested":
                record.color = 4
            else:
                if record.validate:
                    record.color = 10
                else:
                    record.color = 3

    @api.depends("date_start", "date_stop", "validate")
    def _compute_available_facility_ids(self):
        """Compute facilities available for selection.

        - validate=False -> no restriction (all facilities)
        - validate=True  -> restrict to available in given dates
        - validate=True but missing dates -> empty set
        """
        facility_obj = self.env["facility.facility"]

        for record in self:
            if not record.validate:
                available_set = facility_obj.search(TRUE_DOMAIN)

            elif record.date_start and record.date_stop:
                available_set = facility_obj.available(
                    date_start=record.date_start,
                    date_stop=record.date_stop,
                    exclude_reservation_ids=record._origin.ids,
                )

            else:
                available_set = facility_obj.browse()

            record.available_facility_ids = available_set

    @api.depends(
        "name",
        "facility_id",
        "facility_id.name",
        "facility_id.complex_id",
        "facility_id.complex_id.name",
        "manager_id",
        "manager_id.name",
    )
    @api.depends_context("lang")
    def _compute_display_name(self):
        """Computes a single facility display name

        This is a private user-defined method, Not to be confused with the
        ``name_get`` starndard public method.

        Returns:
            str: name will be shown in GUI
        """

        for record in self:
            if record.name:
                record.display_name = record.name

            elif record.facility_id:
                facility = record.facility_id.name

                facility_complex = record.facility_id.complex_id
                uid_is_allowed = (
                    facility_complex
                    and facility_complex.is_an_allowed_supervisor()
                )

                if uid_is_allowed and record.manager_id:
                    manager = record.manager_id.name
                    record.display_name = f"{facility} - {manager}"
                else:
                    record.display_name = f"{facility}"
            else:
                record.display_name = _("New facility")

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains("name")
    def _check_name_length(self):
        for rec in self:
            n = (rec.name or "").strip()  # valor en el idioma activo
            if n and len(n) < 5:
                raise ValidationError(
                    _("The name must be at least 5 characters long.")
                )

    # -------------------------------------------------------------------------
    # ORM METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        message = _(
            "You lack permission to confirm reservations in this complex"
        )

        defaults = self.default_get(["state", "facility_id"])

        for vals in vals_list:
            effective_values = {
                **defaults,
                **vals,
            }

            if not self.is_authorized_to_confirm(effective_values):
                raise ValidationError(message)

        return super().create(vals_list)

    def write(self, values):
        """Overridden method 'write'."""

        if values.get("state") == "rejected" and str2bool(
            self.get_param("auto_archive_on_rejection", False),
            default=False,
        ):
            values["active"] = False

        if not self.is_authorized_to_confirm(values):
            message = _(
                "You lack permission to confirm reservations in this complex"
            )
            raise ValidationError(message)

        return super().write(values)

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()

        _super = super()

        default = dict(default or {})

        default["date_start"] = self.date_start + timedelta(days=7)
        default["date_stop"] = self.date_stop + timedelta(days=7)

        return _super.copy(default=default)

    # -------------------------------------------------------------------------
    # SCHEDULER
    # -------------------------------------------------------------------------

    def _ensure_scheduler(self):
        self.ensure_one()

        if self.scheduler_id:
            return self.scheduler_id

        mixin = self.env["facility.scheduler.mixin"]

        date_start = self.date_start.strftime("%Y-%m-%d %H:%M:%S")
        date_base, time_start = mixin.split_datetime(date_start)

        date_stop = self.date_stop.strftime("%Y-%m-%d %H:%M:%S")
        time_stop = mixin.split_datetime(date_stop)[1]

        scheduler_values = {
            "date_base": date_base,
            "time_start": time_start,
            "time_stop": time_stop,
            "name": self.name,
            "description": self.description,
            "active": self.active,
            "facility_id": self.facility_id.id,
            "confirm": self.state == "confirmed",
            "validate": self.validate,
            "owner_id": self.owner_id.id,
            "subrogate_id": self.subrogate_id.id,
        }

        scheduler_obj = self.env["facility.reservation.scheduler"]
        scheduler = scheduler_obj.with_context(
            skip_make_reservations=True
        ).create(scheduler_values)

        self.scheduler_id = scheduler

        return scheduler

    def view_scheduler(self, force=False):
        self.ensure_one()

        if force and not self.scheduler_id:
            self._ensure_scheduler()

        if not self.scheduler_id:
            msg = _("This facility reservation has no associated scheduler")
            raise UserError(msg)

        xid = (
            "facility_management."
            "action_facility_reservation_scheduler_as_wizard_act_window"
        )
        action = self.env.ref(xid)

        ctx = self.env.context.copy()
        ctx.update(safe_eval(action.context))
        ctx.update({"default_facility_id": self.facility_id.id})

        # Required to be called from facility_search_available_wizard button
        ctx.pop("list_view_ref", False)

        serialized = {
            "type": "ir.actions.act_window",
            "res_model": "facility.reservation.scheduler",
            "res_id": self.scheduler_id.id,
            "target": "new",
            "name": action.name,
            "view_mode": "form",
            "domain": [],
            "context": ctx,
            "search_view_id": action.search_view_id.id,
            "help": action.help
            # , 'flags': {'mode': 'readonly'}
        }

        return serialized

    def unbind(self):
        self.write({"scheduler_id": False})

    # -------------------------------------------------------------------------
    # AUTHORIZATION
    # -------------------------------------------------------------------------

    def _uid_is_manager(self):
        group_manager = "facility_management.facility_group_manager"
        return self.env.user.has_group(group_manager)

    def is_authorized_to_confirm(self, values):
        """Check authorization for the effective state and facility."""

        facility_obj = self.env["facility.facility"]

        # Called from write().
        if self:
            # Nothing affecting confirmation authorization is being changed.
            if not {"state", "facility_id"} & values.keys():
                return True

            for record in self:
                state = values.get("state", record.state)

                if state != "confirmed":
                    continue

                if "facility_id" in values:
                    facility = facility_obj.browse(values["facility_id"])
                else:
                    facility = record.facility_id

                if (
                    facility
                    and not facility.complex_id.is_an_allowed_supervisor()
                ):
                    return False

            return True

        # Called from create(). Values already include relevant defaults.
        if values.get("state") != "confirmed":
            return True

        facility_id = values.get("facility_id")
        if not facility_id:
            return True

        facility = facility_obj.browse(facility_id)

        return facility.complex_id.is_an_allowed_supervisor()

    # -------------------------------------------------------------------------
    # MAIL THREAD
    # -------------------------------------------------------------------------

    def _track_subtype(self, init_values):
        self.ensure_one()

        fmt = "facility_management.message_subtype_facility_reservation_%s"

        if "state" in init_values:
            if self.state == "confirmed":
                return self.env.ref(fmt % "state_confirmed")

            if self.state == "rejected":
                return self.env.ref(fmt % "state_rejected")

            if self.state == "requested":
                return self.env.ref(fmt % "state_pending")

        return self.env.ref(fmt % "has_updated")

    def _get_message_subtype_reservation_state_ids(self):
        xml_ids = [
            (
                "facility_management."
                "message_subtype_facility_reservation_state_pending"
            ),
            (
                "facility_management."
                "message_subtype_facility_reservation_state_confirmed"
            ),
            (
                "facility_management."
                "message_subtype_facility_reservation_state_rejected"
            ),
        ]

        subtype_set = self.env["mail.message.subtype"]
        for xmlid in xml_ids:
            subtype_set |= self.env.ref(xmlid)

        return subtype_set

    def _get_message_subtype_reservation_ids(self):
        updated_xid = (
            "facility_management."
            "message_subtype_facility_reservation_has_updated"
        )
        subtype_set = self._get_message_subtype_reservation_state_ids()
        subtype_set |= self.env.ref(updated_xid)

        return subtype_set

    def _notify_by_email_render_layout(
        self,
        message,
        recipients_group,
        msg_vals=False,
        render_values=None,
    ):
        subtype_id = (
            msg_vals.get("subtype_id")
            if msg_vals and "subtype_id" in msg_vals
            else message.subtype_id.id
        )

        state_subtype_ids = (
            self._get_message_subtype_reservation_state_ids().ids
        )

        updated_subtype_id = self.env.ref(
            "facility_management."
            "message_subtype_facility_reservation_has_updated"
        ).id

        if subtype_id in state_subtype_ids:
            msg_vals = dict(msg_vals or {})
            msg_vals["email_layout_xmlid"] = (
                "facility_management."
                "facility_reservation_state_changed_email"
            )

        elif subtype_id == updated_subtype_id:
            msg_vals = dict(msg_vals or {})
            msg_vals["email_layout_xmlid"] = (
                "facility_management." "facility_reservation_has_changed_email"
            )

        return super()._notify_by_email_render_layout(
            message,
            recipients_group,
            msg_vals=msg_vals,
            render_values=render_values,
        )

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients_data = super()._notify_get_recipients(
            message,
            msg_vals,
            **kwargs,
        )

        subtype_id = (
            msg_vals.get("subtype_id")
            if msg_vals and "subtype_id" in msg_vals
            else message.subtype_id.id
        )

        subtype_ids = self._get_message_subtype_reservation_ids().ids

        if subtype_id not in subtype_ids:
            return recipients_data

        message_type = (
            msg_vals.get("message_type")
            if msg_vals and "message_type" in msg_vals
            else message.message_type
        )

        email_partner_set = (
            self.complex_id.partner_id | self.manager_id.partner_id
        )

        inbox_partner_set = (
            self.complex_id.supervisor_ids.partner_id - email_partner_set
        )

        excluded_partner_ids = set()

        if kwargs.get("skip_existing"):
            notifications = (
                self.env["mail.notification"]
                .sudo()
                .search(
                    [
                        ("mail_message_id", "=", message.id),
                        (
                            "res_partner_id",
                            "in",
                            (email_partner_set | inbox_partner_set).ids,
                        ),
                    ]
                )
            )

            excluded_partner_ids = set(notifications.res_partner_id.ids)

        self._set_notification_recipients(
            recipients_data=recipients_data,
            partner_set=email_partner_set,
            excluded_partner_ids=excluded_partner_ids,
            message_type=message_type,
            subtype_id=subtype_id,
            notification_type="email",
        )

        self._set_notification_recipients(
            recipients_data=recipients_data,
            partner_set=inbox_partner_set,
            excluded_partner_ids=excluded_partner_ids,
            message_type=message_type,
            subtype_id=subtype_id,
            notification_type="inbox",
        )

        return recipients_data

    def _set_notification_recipients(
        self,
        recipients_data,
        partner_set,
        excluded_partner_ids,
        message_type,
        subtype_id,
        notification_type,
    ):
        partner_set = partner_set.filtered(
            lambda partner: partner.id not in excluded_partner_ids
        )

        if not partner_set:
            return

        recipient_data = (
            self.env["mail.followers"]
            ._get_recipient_data(
                self,
                message_type,
                subtype_id,
                partner_set.ids,
            )
            .get(self.id, {})
        )

        current_data = {values["id"]: values for values in recipients_data}

        for partner in partner_set:
            if notification_type == "email" and not partner.email:
                continue

            values = current_data.get(partner.id)

            if values:
                values["notif"] = notification_type
                continue

            values = recipient_data.get(partner.id)

            if not values or not values.get("active"):
                continue

            values = dict(values)
            values["notif"] = notification_type

            recipients_data.append(values)
            current_data[partner.id] = values

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    @api.model
    def get_param(self, param_name, default):
        param_obj = self.env["ir.config_parameter"].sudo()

        full_param_name = f"facility_management.{param_name}"

        return param_obj.get_param(full_param_name, default)

    # -------------------------------------------------------------------------
    # DATE AND TIME UTILITIES
    # -------------------------------------------------------------------------

    @staticmethod
    def now_o_clock(offset_hours=0, round_up=False):
        present = fields.Datetime.now()
        oclock = present.replace(minute=0, second=0, microsecond=0)

        if round_up and (oclock < present):  # almost always
            oclock += timedelta(hours=1)

        return oclock + timedelta(hours=offset_hours)

    def get_tz(self):
        """Retrieve session timezone if available.

        The timezone can correspond, in order of priority, to:
        1) The complex pertaining to the main classroom.
        2) The company associated with the session.
        3) The administrator of the session.
        4) Default to Coordinated Universal Time (UTC).

        Returns:
            pytz.timezone: Timezone instance or UTC if not found.
        """

        self.ensure_one()

        tz = self.mapped("facility_id.complex_id.partner_id.tz")
        if not tz:
            tz = self.mapped("facility_id.complex_id.company_id.partner_id.tz")
        if not tz:
            tz = self.mapped("facility_id.complex_id.manager_id.partner_id.tz")

        tz = tz and tz[0] or "UTC"  # First value in list or 'UTC'

        return pytz.timezone(tz)

    def get_localized(self, field, strftime=None):
        """
        Converts and localizes a given datetime or date value to the specified
        timezone.

        Returns:
            datetime: localized date or datetime
        """

        self.ensure_one()

        value = getattr(self, field)
        tz = self.get_tz()

        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, date):
            dt = datetime.combine(value, time.min)
        else:
            return value

        dt = pytz.utc.localize(dt)
        dt = dt.astimezone(tz)

        return dt.strftime(strftime) if strftime else dt
