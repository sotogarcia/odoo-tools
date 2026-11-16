###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from datetime import timedelta
from logging import getLogger
from operator import eq, ge, gt, le, lt, ne

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import FALSE_DOMAIN
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _

from ..utils.helpers import (
    check_unique_translation,
    get_available_copy_value,
    one2many_count,
    one2many_count_search_domain,
)

_logger = getLogger(__name__)


class FacilityFacility(models.Model):
    """Facility, like a classroom, laboratory, workshop,..."""

    _name = "facility.facility"
    _description = "Facility"

    _rec_name = "name"
    _order = "complex_id, name ASC"

    _inherit = [  # noqa: RUF012
        "ownership.mixin",
        "image.mixin",
        "mail.thread",
    ]

    _check_company_auto = True

    name = fields.Char(
        string="Name",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Name of the facility",
        size=50,
        translate=True,
        tracking=True,  # track_visibility deprecated; use tracking
    )

    code = fields.Char(
        string="Internal code",
        required=True,
        readonly=False,
        index=False,
        default=None,
        help="Facility internal code",
        size=64,
        translate=False,
    )

    description = fields.Text(
        string="Description",
        required=False,
        readonly=False,
        index=False,
        default=None,
        help="Enter new description",
        translate=True,
    )

    active = fields.Boolean(
        string="Active",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="Enables/disables the record",
    )

    type_id = fields.Many2one(
        string="Type",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Type of facility",
        comodel_name="facility.type",
        domain=[],
        context={},
        ondelete="restrict",
        auto_join=False,
    )

    is_space = fields.Boolean(
        related="type_id.is_space",
        store=True,
        index=True,
    )

    complex_id = fields.Many2one(
        string="Complex",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Complex the facility belongs to",
        comodel_name="facility.complex",
        domain=[],
        context={},
        ondelete="restrict",
        auto_join=False,
    )

    company_id = fields.Many2one(
        related="complex_id.company_id",
        store=True,
        index=True,
    )

    users = fields.Integer(
        string="Users",
        required=True,
        readonly=False,
        index=True,
        default=0,
        help="Maximum concurrent students for this facility",
    )

    @api.onchange("users")
    def _onchange_users(self):
        self.excess = max(self.users, self.excess)

    excess = fields.Integer(
        string="Excess",
        required=True,
        readonly=False,
        index=False,
        default=0,
        help="Max concurrent student invitations for this feature",
    )

    users_str = fields.Char(
        string="Users / Excess users",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Maximum users/maximum excess users",
        size=21,
        translate=False,
        compute="_compute_users_str",
    )

    @api.depends("users", "excess")
    def _compute_users_str(self):
        for record in self:
            if record.users <= 0:
                record.users_str = ""
            elif record.excess > record.users:
                record.users_str = (
                    f"{record.users} (+{record.excess - record.users})"
                )
            else:
                record.users_str = f"{record.users}"

    reservation_ids = fields.One2many(
        string="Reservations",
        required=False,
        readonly=True,
        default=None,
        help="Show related reservations",
        comodel_name="facility.reservation",
        inverse_name="facility_id",
        domain=[],
        context={},
        auto_join=False,
        copy=False,
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

    @api.depends(
        "reservation_ids",
        "reservation_ids.active",
    )
    def _compute_reservation_count(self):
        counts = one2many_count(self, "reservation_ids")

        for record in self:
            record.reservation_count = counts.get(record.id, 0)

    @api.model
    def _search_reservation_count(self, operator, value):
        return one2many_count_search_domain(
            self,
            "reservation_ids",
            operator,
            value,
        )

    next_use = fields.Datetime(
        string="Next use",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Next time this facility will be used",
        compute="_compute_next_use",
        search="_search_next_use",
    )

    @api.depends(
        "reservation_ids",
        "reservation_ids.active",
        "reservation_ids.state",
        "reservation_ids.date_start",
        "reservation_ids.date_stop",
        "reservation_ids.validate",
    )
    def _compute_next_use(self):
        now = fields.Datetime.now()

        domain = [
            ("facility_id", "in", self.ids),
            ("active", "=", True),
            ("state", "=", "confirmed"),
            ("date_stop", ">", now),
            ("validate", "=", True),
        ]

        reservation_obj = self.env["facility.reservation"]
        grouped_data = reservation_obj.read_group(
            domain=domain,
            fields=["facility_id", "next_use:min(date_start)"],
            groupby=["facility_id"],
            lazy=False,
        )

        next_use_by_facility = {
            row["facility_id"][0]: row["next_use"]
            for row in grouped_data
            if row.get("facility_id")
        }

        for record in self:
            record.next_use = next_use_by_facility.get(record.id)

    @api.model
    def _search_next_use(self, operator, value):
        operators = {
            "=": eq,
            "!=": ne,
            "<": lt,
            "<=": le,
            ">": gt,
            ">=": ge,
        }

        if operator not in operators:
            raise UserError(_("Operator not implemented"))

        now = fields.Datetime.now()

        domain = [
            ("active", "=", True),
            ("state", "=", "confirmed"),
            ("date_stop", ">", now),
            ("validate", "=", True),
        ]

        reservation_obj = self.env["facility.reservation"]
        grouped_data = reservation_obj.read_group(
            domain=domain,
            fields=["facility_id", "next_use:min(date_start)"],
            groupby=["facility_id"],
            lazy=False,
        )

        next_use_by_facility = {
            row["facility_id"][0]: fields.Datetime.to_datetime(row["next_use"])
            for row in grouped_data
            if row.get("facility_id") and row.get("next_use")
        }

        if value is False:
            facility_ids = list(next_use_by_facility)

            if operator == "=":
                return [("id", "not in", facility_ids)]

            if operator == "!=":
                return [("id", "in", facility_ids)]

            raise UserError(_("Operator not implemented for empty dates"))

        date_value = fields.Datetime.to_datetime(value)
        compare = operators[operator]

        facility_ids = [
            facility_id
            for facility_id, next_use in next_use_by_facility.items()
            if compare(next_use, date_value)
        ]

        if operator == "!=":
            return [
                "|",
                ("id", "in", facility_ids),
                ("id", "not in", list(next_use_by_facility)),
            ]

        return [("id", "in", facility_ids)]

    color = fields.Integer(
        string="Color",
        required=True,
        readonly=True,
        index=False,
        default=0,
        help="Color will be used in kanban view",
        compute="_compute_color",
    )

    @api.depends("next_use")
    def _compute_color(self):
        now = fields.Datetime.now()

        margin = self._get_availability_margin()
        next_hour = now + timedelta(minutes=margin)

        for record in self:
            if not record.next_use or record.next_use >= next_hour:
                record.color = 10
            elif record.next_use and record.next_use > now:
                record.color = 3
            else:
                record.color = 1

    is_available = fields.Boolean(
        string="Available",
        required=False,
        readonly=True,
        index=False,
        default=False,
        help="True if there are no reservations now or within the next hour.",
        compute="_compute_available",
        search="_search_available",
        store=False,
    )

    @api.depends(
        "reservation_ids",
        "reservation_ids.active",
        "reservation_ids.state",
        "reservation_ids.validate",
        "reservation_ids.date_start",
        "reservation_ids.date_stop",
    )
    def _compute_available(self):
        facility_ids = self.ids
        now = fields.Datetime.now()

        margin = self._get_availability_margin()
        ubound = now + timedelta(minutes=margin)

        domain = [
            ("facility_id", "in", facility_ids),
            ("active", "=", True),
            ("state", "=", "confirmed"),
            ("validate", "=", True),
            ("date_start", "<", ubound),
            ("date_stop", ">", now),
        ]
        groups = self.env["facility.reservation"].read_group(
            domain, ["facility_id"], ["facility_id"]
        )
        counts = {
            g["facility_id"][0]: g["__count"]
            for g in groups
            if g.get("facility_id")
        }
        for rec in self:
            rec.is_available = counts.get(rec.id, 0) == 0

    @api.model
    def _search_available(self, operator, value):
        now = fields.Datetime.now()
        margin = self._get_availability_margin()
        ubound = now + timedelta(minutes=margin)
        groups = self.env["facility.reservation"].read_group(
            [
                ("active", "=", True),
                ("state", "=", "confirmed"),
                ("validate", "=", True),
                ("date_start", "<", ubound),
                ("date_stop", ">", now),
            ],
            ["facility_id"],
            ["facility_id"],
        )
        busy_ids = [
            g["facility_id"][0] for g in groups if g.get("facility_id")
        ]

        # queremos disponibles ⇒ excluir ocupados
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [("id", "not in", busy_ids)] if busy_ids else []
        # queremos no disponibles ⇒ incluir ocupados
        return [("id", "in", busy_ids)] if busy_ids else FALSE_DOMAIN

    _sql_constraints = [  # noqa: RUF012
        (
            "UNIQUE_NAME_BY_COMPLEX",
            "UNIQUE(complex_id, name)",
            "A facility with that name already exists in that complex",
        ),
        (
            "UNIQUE_CODE",
            "UNIQUE(code)",
            "A facility with that code already exists",
        ),
        (
            "USERS_GREATER_OR_EQUAL_TO_ZERO",
            "CHECK(users >= 0)",
            "The number of users must be greater than or equal to zero",
        ),
        (
            "EXCESS_GREAT_OR_EQUAL_THAN_USERS",
            "CHECK(excess >= users)",
            (
                "The number of users that can be invited must be greater than"
                "or equal to the number of users that can use the facility"
            ),
        ),
    ]

    @api.constrains("name", "complex_id")
    def _check_unique_name_by_complex(self):
        check_unique_translation(
            self.sudo(),
            field_name="name",
            domain=lambda record: [("complex_id", "=", record.complex_id.id)],
            message=_("Duplicate facility name in this complex"),
        )

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()

        default = dict(default or {})

        code = get_available_copy_value(
            self,
            field_name="code",
            value=self.code,
            max_length=36,
        )

        name = get_available_copy_value(
            self,
            field_name="name",
            value=self.name,
            domain=[("complex_id", "=", self.complex_id.id)],
        )

        default.update({"name": name, "code": code})

        return super().copy(default)

    @api.depends_context("lang", "facility_name_with_complex")
    @api.depends("name", "complex_id", "complex_id.name")
    def _compute_display_name(self):
        """Build display_name safely even when values are falsy in onchanges."""
        with_complex = self.env.context.get(
            "facility_name_with_complex", False
        )

        for record in self:
            parts = []
            if with_complex and record.complex_id and record.complex_id.name:
                parts.append(record.complex_id.name)
            if record.name:
                parts.append(record.name)
            # Ensure every piece is str and avoid TypeError on join
            record.display_name = " / ".join(map(str, parts)) if parts else ""

    def view_reservations(self):
        self.ensure_one()

        action_xid = "facility_management." "action_reservations_act_window"
        action = self.env.ref(action_xid)

        ctx = self.env.context.copy()
        ctx.update(safe_eval(action.context))
        ctx.update({"default_facility_id": self.id})

        # Required to be called from facility_search_available_wizard button
        ctx.pop("list_view_ref", False)

        domain = [("facility_id", "=", self.id)]
        name = _("{} - Reservations").format(self.name)

        serialized = {
            "type": "ir.actions.act_window",
            "res_model": "facility.reservation",
            "target": "current",
            "name": name,
            "view_mode": action.view_mode,
            "domain": domain,
            "context": ctx,
            "search_view_id": action.search_view_id.id,
            "help": action.help,
        }

        return serialized

    @api.model
    def available(
        self,
        date_start=None,
        date_stop=None,
        type_ids=None,
        exclude_reservation_ids=None,
    ):
        if not date_start:
            if not date_stop:
                date_start = fields.Datetime.now()
            else:
                date_start = date_stop - timedelta(hours=1)

        if not date_stop:
            date_stop = date_start + timedelta(hours=1)

        reservation_obj = self.env["facility.reservation"]
        reservation_domain = [
            ("active", "=", True),
            ("state", "=", "confirmed"),
            ("validate", "=", True),
            ("date_start", "<", date_stop),
            ("date_stop", ">", date_start),
        ]

        if exclude_reservation_ids:
            reservation_domain.append(
                ("id", "not in", exclude_reservation_ids)
            )

        reservation_set = reservation_obj.search(reservation_domain)

        facility_obj = self.env["facility.facility"]
        facility_domain = []

        exclude_ids = reservation_set.mapped("facility_id.id")
        if exclude_ids:
            exclude_leaf = ("id", "not in", exclude_ids)
            facility_domain.append(exclude_leaf)

        if type_ids:
            if isinstance(type_ids, models.Model):
                type_ids = type_ids.mapped("id")

            type_leaf = ("type_id", "in", type_ids)
            facility_domain.append(type_leaf)

        msg = "Search available facilities: {}"
        _logger.debug(msg.format(facility_domain))
        facility_set = facility_obj.search(facility_domain)

        return facility_set

    def _get_availability_margin(self):
        """Return the configured availability margin in minutes,
        or 60 if not set or invalid.
        """
        param_xid = "facility_management.availability_margin_minutes"
        config = self.env["ir.config_parameter"].sudo()

        try:
            param_value = config.get_param(param_xid, "60")
            param_value = int(param_value)
        except (TypeError, ValueError):
            message = _("Invalid availability margin configuration")
            _logger.exception(message)
            param_value = 60

        return param_value


# 1 -> Naranja oscuro
# 2 -> Naranja
# 3 -> Amarillo
# 4 -> Azul claro
# 5 -> Morado
# 6 -> Rosa oscuro
# 7 -> Azul verdoso
# 8 -> Azul oscuro
# 9 -> Rojo/magenta
# 10 -> Verde
# 11 -> Violeta
