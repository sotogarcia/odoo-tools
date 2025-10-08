# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools.safe_eval import safe_eval
from odoo.osv.expression import TRUE_DOMAIN, FALSE_DOMAIN
from odoo.exceptions import UserError
from ..utils.helpers import OPERATOR_MAP, one2many_count

from datetime import datetime, timedelta

from logging import getLogger
from math import trunc, pow
from random import random
from re import sub


_logger = getLogger(__name__)


class FacilityFacility(models.Model):
    """Facility, like a classroom, laboratory, workshop,..."""

    _name = "facility.facility"
    _description = "Facility"

    _rec_name = "name"
    _order = "complex_id, name ASC"

    _inherit = ["image.mixin", "ownership.mixin", "mail.thread"]

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
        size=36,
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
        ondelete="cascade",
        auto_join=False,
    )

    is_space = fields.Boolean(
        string="Is space",
        required=False,
        readonly=False,
        index=True,
        default=False,
        help="Check this option if the record represents a physical space.",
        related="type_id.is_space",
        store=True,
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
        ondelete="cascade",
        auto_join=False,
    )

    company_id = fields.Many2one(
        string="Company", related="complex_id.company_id", store=True
    )

    users = fields.Integer(
        string="Users",
        required=True,
        readonly=False,
        index=True,
        default=0,
        help=(
            "Maximum number of students who can use this facility at the "
            "same time"
        ),
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
        help=(
            "Maximum number of students who can be invited to use this "
            "feature at the same time"
        ),
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
                record.users_str = "{} (+{})".format(
                    record.users, record.excess - record.users
                )
            else:
                record.users_str = "{}".format(record.users)

    reservation_ids = fields.One2many(
        string="Reservations",
        required=False,
        readonly=False,
        index=True,
        default=None,
        help="Show related reservations",
        comodel_name="facility.reservation",
        inverse_name="facility_id",
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

    @api.depends("reservation_ids")
    def _compute_next_use(self):
        now = fields.Datetime.now()

        for record in self:
            reservation_set = record.reservation_ids
            reservation_set = reservation_set.sorted(lambda x: x.date_start)
            reservation_set = reservation_set.filtered(
                lambda x: x.date_stop >= now
            )

            if not reservation_set:
                record.next_use = None
            else:
                record.next_use = reservation_set[0].date_start

    @api.model
    def _search_next_use(self, operator, value):
        """This uses SQL ``tsrange`` to search valid facilities. Returns a
        domain with valid IDs.

        All the operators compare the user-supplied date/time value with any of
        the values in the date/time range of the reservation used to calculate
        the value of ``next_use`` field.

        NOTE: the behavior of the method for those cases where the user selects
        "between" may be abnormal.

        NOTE: Only active and confirmed reservations will be used.

        Args:
            operator (str): the operator that has been chosen by the user
            value (datetime|bool): value that has been given by the user

        Returns:
            list: domain like [('id', 'in', facility_ids)]

        Raises:
            UserError: if the given operator has not been considered for this
            implementation.
        """

        sql = self._search_next_use_sql
        TSR = """
            {nq} date_range
            {op} tsrange(\'{dt}\'::TIMESTAMP, \'{dt}\'::TIMESTAMP, \'[]\')
        """

        domain = FALSE_DOMAIN

        # '=', '!=', '<=', '<', '>', '>='
        if value is False:
            if operator == "=":  # next_use is not set
                clausule = "date_range IS NULL"
            else:  # next_use is set
                clausule = "date_range IS NOT NULL"
        elif operator == "=":
            clausule = TSR.format(nq="", dt=value, op="@>")
        elif operator == "!=":
            clausule = TSR.format(nq="NOT", dt=value, op="@>")
        elif operator == "<":
            clausule = TSR.format(nq="", dt=value, op="<<")
        elif operator == "<=":
            clausule = TSR.format(nq="", dt=value, op="&<")
        elif operator == ">":
            clausule = TSR.format(nq="", dt=value, op=">>")
        elif operator == ">=":
            clausule = TSR.format(nq="", dt=value, op="&>")
        else:
            raise UserError("Operator not implemented")

        sql = sql.format(clausule=clausule)
        self.env.cr.execute(sql)
        rows = self.env.cr.dictfetchall()

        if rows:
            facility_ids = [row["facility_id"] for row in (rows or [])]
            domain = [("id", "in", facility_ids)]

        return domain

    _search_next_use_sql = """
        WITH active_reservations AS (
            SELECT
                "id" AS reservation_id,
                facility_id,
                date_start,
                date_stop
            FROM
                facility_reservation
            WHERE
                active
                AND STATE = 'confirmed'
                AND date_stop >= CURRENT_TIMESTAMP AT TIME ZONE 'utc'
        ), targets AS (
            SELECT
                aef."id" AS facility_id,
                CASE WHEN date_start IS NOT NULL AND date_stop IS NOT NULL
                    THEN tsrange(date_start, date_stop, '[]')
                    ELSE NULL
                END AS date_range
            FROM
                facility_facility AS aef
            LEFT JOIN active_reservations AS ar
                ON aef."id" = ar.facility_id
            WHERE
                aef.active
        ) SELECT
            *
        FROM targets
        WHERE {clausule}
    """

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
        now = datetime.now()

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
        print("_search_available")
        now = fields.Datetime.now()
        ubound = now + timedelta(hours=1)
        groups = self.env["facility.reservation"].read_group(
            [("date_start", "<", ubound), ("date_stop", ">", now)],
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

    _sql_constraints = [
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

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})

        rand = str(trunc(random() * pow(10, 15))).zfill(15)
        cursor = self.env.cr

        sql = """
            SELECT
                ( '{part}' || gs )::VARCHAR AS "value"
            FROM
                generate_series ( 1, 999999, 1 ) AS gs
            LEFT JOIN facility_facility AS ff
                ON ff."{field}" = ( '{part}' || gs ) {on}
            WHERE
                ff."id" IS NULL
                LIMIT 1;
        """

        code = sub("[0-9]+$", "", self.code)
        cursor.execute(sql.format(on="", part=code, field="code"))
        row = cursor.dictfetchone()
        if not row or len(row["value"]) > 30:
            code = rand
        else:
            code = row["value"]

        name = sub("[0-9]$", "", self.name)
        on = "AND ff.complex_id = {}".format(self.complex_id.id)
        cursor.execute(sql.format(on=on, part=name, field="name"))
        row = cursor.dictfetchone()
        name = rand if not row else row["value"]

        default.update({"name": name, "code": code})

        return super(FacilityFacility, self).copy(default)

    @api.depends_context("lang")
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
    def available(self, date_start=None, date_stop=None, type_ids=None):
        if not date_start:
            if not date_stop:
                date_start = fields.Datetime.now()
            else:
                date_start = date_stop - timedelta(hours=1)

        if not date_stop:
            date_stop = date_start + timedelta(hours=1)

        reservation_obj = self.env["facility.reservation"]
        reservation_domain = [
            "|",
            "&",
            ("date_start", ">=", date_start),
            ("date_start", "<", date_stop),
            "&",
            ("date_stop", ">", date_start),
            ("date_stop", "<", date_stop),
        ]
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
        except (TypeError, ValueError) as ex:
            _logger.error(
                "Invalid availability margin configuration: %s",
                ex,
                exc_info=True,
            )
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
