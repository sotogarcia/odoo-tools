# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools.safe_eval import safe_eval
from odoo.osv.expression import AND, TRUE_DOMAIN, FALSE_DOMAIN
from odoo.exceptions import ValidationError
from ..utils.helpers import OPERATOR_MAP, one2many_count, many2many_count

from logging import getLogger
from math import trunc, pow
from random import random
from re import sub
from datetime import datetime


_logger = getLogger(__name__)


class FacilityComplex(models.Model):
    """A group of facilities, usually in the same location"""

    _name = "facility.complex"
    _description = "Facility complex"

    _rec_name = "name"
    _order = "name ASC"

    _inherit = ["image.mixin", "ownership.mixin", "mail.thread"]

    _inherits = {"res.partner": "partner_id"}

    _check_company_auto = True

    partner_id = fields.Many2one(
        string="Partner",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Contact information",
        comodel_name="res.partner",
        domain=[],
        context={},
        ondelete="restrict",
        auto_join=False,
    )

    # Overwritten field
    company_id = fields.Many2one(
        string="Company",
        required=True,
        readonly=True,
        index=True,
        default=lambda self: self.env.company,
        help="The company this record belongs to",
        comodel_name="res.company",
        domain=[],
        context={},
        ondelete="cascade",
        auto_join=False,
    )

    code = fields.Char(
        string="Internal code",
        required=True,
        readonly=False,
        index=False,
        default=None,
        help="Enter new internal code",
        size=36,
        translate=False,
    )

    description = fields.Html(
        string="Description",
        help="Enter new description",
        related="partner_id.comment",
    )

    facility_ids = fields.One2many(
        string="Facilities",
        required=False,
        readonly=False,
        index=True,
        default=None,
        help="Facilities in this complex",
        comodel_name="facility.facility",
        inverse_name="complex_id",
        domain=[],
        context={},
        auto_join=False,
    )

    facility_count = fields.Integer(
        string="Facility count",
        required=True,
        readonly=True,
        index=False,
        default=0,
        help="Number of active facilities in this complex",
        compute="_compute_facility_count",
        search="_search_facility_count",
    )

    @api.depends("facility_ids", "facility_ids.active")
    def _compute_facility_count(self):
        """Compute count of *active* facilities per complex (batch)."""
        counts = one2many_count(self, "facility_ids")

        for record in self:
            record.facility_count = counts.get(record.id, 0)

    @api.model
    def _search_facility_count(self, operator, value):
        """Search comparing the number of *active* facilities per complex.
        Does not exclude archived complexes.
        """
        # Handle boolean-like searches Odoo may pass for required fields
        if value is True:
            return TRUE_DOMAIN if operator == "=" else FALSE_DOMAIN
        if value is False:
            return TRUE_DOMAIN if operator != "=" else FALSE_DOMAIN

        cmp_func = OPERATOR_MAP.get(operator)
        if not cmp_func:
            return FALSE_DOMAIN  # unsupported operator

        counts = one2many_count(self.search([]), "facility_ids")
        matched = [cid for cid, cnt in counts.items() if cmp_func(cnt, value)]

        return [("id", "in", matched)] if matched else FALSE_DOMAIN

    space_ids = fields.One2many(
        string="Spaces",
        required=False,
        readonly=False,
        index=True,
        default=None,
        help="Spaces in this complex",
        comodel_name="facility.facility",
        inverse_name="complex_id",
        domain=[("is_space", "=", True)],
        context={},
        auto_join=False,
    )

    space_count = fields.Integer(
        string="Space count",
        required=True,
        readonly=True,
        index=False,
        default=0,
        help="Number of active spaces in this complex",
        compute="_compute_space_count",
    )

    @api.depends("space_ids", "space_ids.is_space")
    def _compute_space_count(self):
        """Compute count of *active* facilities per complex (batch)."""
        counts = one2many_count(self, "space_ids")

        for record in self:
            record.space_count = counts.get(record.id, 0)

    users = fields.Integer(
        string="Seats",
        required=False,
        readonly=True,
        index=False,
        default=0,
        help="Total user capacity across all facilities in this complex",
        compute="_compute_users",
    )

    @api.depends("facility_ids", "facility_ids.users")
    def _compute_users(self):
        for record in self:
            vals = record.facility_ids.mapped("users")
            record.users = sum((v or 0) for v in vals)

    supervisor_ids = fields.Many2many(
        string="Supervisors",
        required=False,
        readonly=False,
        index=False,
        default=None,
        help=(
            "Preferred supervisors are primarily designated to approve room "
            "reservations within this complex. Keep in mind users should "
            "have the appropriate permissions"
        ),
        comodel_name="res.users",
        relation="facility_complex_res_users_preferred_supervisor_rel",
        column1="complex_id",
        column2="user_id",
        domain=lambda self: self._build_supervisor_ids_domain(),
        context={},
    )

    reservation_ids = fields.Many2manyView(
        string="Reservations",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Reservations linked to this complex (requested state)",
        comodel_name="facility.reservation",
        relation="facility_complex_facility_reservation_rel",
        column1="complex_id",
        column2="reservation_id",
        domain=[("state", "=", "requested")],
        context={},
    )

    reservation_count = fields.Integer(
        string="Reservation count",
        required=True,
        readonly=True,
        index=False,
        default=0,
        help="Total number of reservations made for this facility complex",
        compute="_compute_reservation_count",
    )

    @api.depends("reservation_ids")
    def _compute_reservation_count(self):
        counts = many2many_count(self, "reservation_ids")

        for record in self:
            record.reservation_count = counts.get(record.id, 0)

    unconfirmed_reservation_ids = fields.Many2manyView(
        string="Unconfirmed reservations",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Reservations awaiting confirmation for this complex",
        comodel_name="facility.reservation",
        relation="facility_complex_facility_reservation_rel",
        column1="complex_id",
        column2="reservation_id",
        domain=[("state", "=", "requested")],
        context={},
    )

    unconfirmed_reservation_count = fields.Integer(
        string="Awaiting count",
        required=True,
        readonly=True,
        index=False,
        default=0,
        help=(
            "Total reservations awaiting confirmation for this facility "
            "complex"
        ),
        compute="_compute_unconfirmed_reservation_count",
    )

    @api.depends("unconfirmed_reservation_ids")
    def _compute_unconfirmed_reservation_count(self):
        counts = many2many_count(self, "unconfirmed_reservation_ids")

        for record in self:
            record.unconfirmed_reservation_count = counts.get(record.id, 0)

    display_address = fields.Char(
        string="Display address",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Formatted postal address of the complex (without company)",
        compute="_compute_display_address",
        store=False,
    )

    @api.depends(
        "partner_id",
        "partner_id.name",
        "partner_id.parent_id",
        "partner_id.company_name",
        "partner_id.street",
        "partner_id.street2",
        "partner_id.city",
        "partner_id.zip",
        "partner_id.state_id",
        "partner_id.country_id",
    )
    def _compute_display_address(self):
        for record in self:
            partner = record.partner_id
            record.display_address = (
                partner
                and partner._display_address(without_company=True)
                or False
            )

    phone_number = fields.Char(
        string="Phone number",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Primary phone for the complex (partner phone or mobile",
        compute="_compute_phone_number",
        store=False,
    )

    @api.depends("phone", "mobile")
    def _compute_phone_number(self):
        for record in self:
            partner = record.partner_id
            record.phone_number = partner.phone or partner.mobile or False

    def _build_supervisor_ids_domain(self):
        """
        Retrieve the domain for users primarily designated as preferred
        supervisors.

        This domain is used for the `supervisor_ids` field.

        Returns:
            str: A domain suitable for filtering `res.users`.
        """

        leafs = ['("id", "!=", owner_id)', '("id", "!=", subrogate_id)']

        xmlid = "facility_management.facility_group_monitor"
        group = self.env.ref(xmlid, raise_if_not_found=False)
        if group:
            group_leaf = '("groups_id", "=", {})'.format(group.id)
            leafs.append(group_leaf)

        return "[ {leafs} ]".format(leafs=", ".join(leafs))

    def get_allowed_supervisors(self):
        self.ensure_one()

        xmlid = "facility_management.facility_group_monitor"
        group = self.env.ref(xmlid, raise_if_not_found=True)

        user_set = self.supervisor_ids
        user_set |= self.owner_id
        user_set |= self.subrogate_id

        return user_set.filtered(lambda r: group.id in r.groups_id.ids)

    def is_an_allowed_supervisor(self, user=None):
        """
        Check if a user is authorized as a supervisor.

        A valid supervisor is one who belongs to the facility managers group or
        is listed as a supervisor, owner, or delegate of a complex while also
        being in the facility monitors group.

        Parameters:
            user (res.users|int, optional): User (or user ID) to check.
                Defaults to the current logged-in user.

        Returns:
            bool: True if valid supervisor, else False.

        Raises:
            ValueError: If the user record could not be obtained
        """

        self.ensure_one()

        # Admin and system always are allowed
        super_users = [
            self.env.ref("base.user_admin"),
            self.env.ref("base.user_root"),
        ]
        if self.env.user in super_users:
            return True

        user_obj = self.env["res.users"]

        if not user:
            user = self.env.user
        elif isinstance(user, int):
            user = self.env["res.users"].browse(user)

        if not isinstance(user, type(user_obj)):
            raise ValueError(_("There is no user to check"))

        xmlid = "facility_management.facility_group_manager"
        group = self.env.ref(xmlid, raise_if_not_found=True)

        # Efficient way to verify user's group without loading all IDs
        domain = [("id", "=", user.id), ("groups_id", "=", group.id)]
        if user_obj.search_count(domain) > 0:
            return True

        allowed_set = self.get_allowed_supervisors()
        if not allowed_set:
            return False

        return user in allowed_set

    _sql_constraints = [
        (
            "unique_partner_id",
            'UNIQUE("partner_id")',
            "A complex with the same data already exists",
        ),
        (
            "unique_complex_code",
            'UNIQUE("code")',
            "A complex with this code already exists",
        ),
    ]

    @api.constrains("partner_id")
    def _check_unique_name_by_company(self):
        msg_1 = _("Complex must have a name")
        msg_2 = _(
            "There is already a complex with the same name in this company"
        )

        for record in self:
            partner = record.partner_id
            if not partner or not partner.name or len(partner.name) < 1:
                raise ValidationError(msg_1)
            else:
                res_id = record.id if isinstance(record.id, int) else 0
                complex_domain = [
                    "&",
                    ("id", "!=", res_id),
                    ("name", "ilike", partner.name),
                ]
                complex_obj = self.env["facility.complex"]
                complex_set = complex_obj.search(complex_domain, limit=1)

                if complex_set:
                    raise ValidationError(msg_2)

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})

        rand = str(trunc(random() * pow(10, 15))).zfill(15)
        cursor = self.env.cr

        sql = """
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
        """

        code = sub("[0-9]+$", "", self.code)
        cursor.execute(sql.format(where="", part=code, field="code"))
        row = cursor.dictfetchone()
        if not row or len(row["value"]) > 30:
            code = rand
        else:
            code = row["value"]

        name = sub("[0-9]$", "", self.name)
        where = "AND fc.company_id = {}".format(self.env.company.id)
        cursor.execute(sql.format(where=where, part=name, field="name"))
        row = cursor.dictfetchone()
        name = rand if not row else row["value"]

        default.update({"name": name, "code": code})

        return super(FacilityComplex, self).copy(default)

    @api.model
    def default_get(self, fields):
        parent = super(FacilityComplex, self)
        values = parent.default_get(fields)

        company = self.env.company or self.env.ref("base.main_company")
        values["company_id"] = company.id

        # Keep compatibility across versions: only set if field exists
        if "employee" in self.env["res.partner"]._fields:
            values["employee"] = False

        values["type"] = "other"
        values["is_company"] = False
        # values['company_type'] = 'company'

        return values

    def view_facilities(self):
        self.ensure_one()

        action_xid = "facility_management." "action_facilities_act_window"
        action = self.env.ref(action_xid)

        ctx = self.env.context.copy()
        ctx.update(safe_eval(action.context))
        ctx.update(default_complex_id=self.id)

        domain = [("complex_id", "=", self.id)]

        serialized = {
            "type": "ir.actions.act_window",
            "res_model": "facility.facility",
            "target": "current",
            "name": action.name,
            "view_mode": action.view_mode,
            "domain": domain,
            "context": ctx,
            "search_view_id": action.search_view_id.id,
            "help": action.help,
        }

        return serialized

    def view_reservations(self):
        self.ensure_one()

        action_xid = "facility_management." "action_reservations_act_window"
        action = self.env.ref(action_xid)

        ctx = self.env.context.copy()
        domain = [("complex_id", "=", self.id)]

        serialized = {
            "type": "ir.actions.act_window",
            "res_model": "facility.reservation",
            "target": "current",
            "name": action.name,
            "view_mode": action.view_mode,
            "domain": domain,
            "context": ctx,
            "search_view_id": action.search_view_id.id,
            "help": action.help,
        }

        return serialized

    @api.model
    def _compute_cron_lastcall_domain(self):
        """
        Get the domain based on the last call of a scheduled cron task.

        The domain is used to filter out records before the last call of the
        associated cron task, to ensure we're only processing new or updated
        records since the last task run.

        Returns:
            list: domain based on the last call of a scheduled cron task
        """

        xmlid = "facility_management.ir_cron_notify_reservation_requests"
        cron_task = self.env.ref(xmlid, raise_if_not_found=False)
        lastcall = cron_task and cron_task.lastcall or datetime.min

        cron_domain = [
            "|",
            ("write_date", "=", False),
            ("write_date", ">", fields.Datetime.to_string(lastcall)),
        ]

        return cron_domain

    def _compute_requested(self, cron_domain=None, filter_domain=None):
        """
        Retrieve reservations in complex that are in a 'requested' state and
        also match the provided cron_domain and filter_domain (if any).

        Args:
            cron_domain (list, optional): domain to filter reservations
                                          based on the last cron job run time.
            filter_domain (list, optional): additional filtering constraints
                                            on the reservations.

        Returns:
            models.Model: A recordset containing reservations that match the
                          given criteria
        """

        self.ensure_one()

        reservation_obj = self.env["facility.reservation"]

        requested_domain = [("state", "=", "requested")]

        facility_ids = self.mapped("facility_ids.id")
        facility_domain = [("facility_id", "in", facility_ids)]

        domains = [facility_domain, requested_domain]

        if cron_domain:
            domains.append(cron_domain)

        if filter_domain:
            domains.append(filter_domain)

        reservation_domain = AND(domains)
        reservation_set = reservation_obj.search(reservation_domain)

        return reservation_set

    @staticmethod
    def _compute_row(reservation, facility_url, reservation_url):
        """Get a dictionary with the reservation data, formatted and ready for
        inclusion in an notification email.

        Args:
            reservation (models.Model): target facility reservation
            facility_url (str): URL without resource ID relative to the form
                                view for the facility.facility model.
            reservation_url (str): URL without resource ID relative to the form
                                   view for the facility.reservation model.

        Returns:
            dict: reservation data, formatted and ready for inclusion in email
        """

        reservation.ensure_one()

        facility = reservation.facility_id
        manager = reservation.manager_id

        row = {
            "id": reservation.id,
            "facility": facility.name,
            "facility_url": facility_url.format(facility.id),
            "manager": manager.name,
            "manager_email": manager.email,
            "manager_phone": manager.phone,
            "url": reservation_url.format(reservation.id),
            "date_start": reservation.get_localized("date_start", "%c"),
            "date_stop": reservation.get_localized("date_stop", "%c"),
            "create_date": reservation.get_localized("create_date", "%c"),
        }

        return row

    def _compute_rows(self, cron_domain=None, filter_domain=None):
        """Get a list of formatted reservation dictionaries will be used as
        reservation data, formatted and ready for inclusion in email
        notifications.

        Args:
            cron_domain (list, optional): domain to filter reservations
                                          based on the last cron job run time.
            filter_domain (list, optional): additional filtering constraints
                                            on the reservations.

        Returns:
            models.Model: A recordset containing reservations that match the
                          given criteria
        """

        reservation_set = self._compute_requested(cron_domain, filter_domain)

        reservation_url = self._get_form_view_base_url(
            "facility.reservation", "facility_management.menu_reservations"
        )
        facility_url = self._get_form_view_base_url(
            "facility.facility", "facility_management.menu_facilities"
        )

        rows = []
        if reservation_set:
            for reservation in reservation_set:
                row = self._compute_row(
                    reservation, facility_url, reservation_url
                )

                rows.append(row)

        return rows

    def notify_reservation_requests(self, filter_domain=False, is_cron=False):
        """Send notifications about pending facility reservation requests.

        This method sends email notifications about reservation requests that
        are awaiting approval, using the provided filter and based on whether
        it's triggered by the cron or manually.

        Args:
            filter_domain (list, optional): additional filtering constraints
                                            on the reservations.
            is_cron (bool, optional): True to notify all pending reservation
                                      requests since the last cron task call
                                      or False to notify pending reservations
                                      related with the current recordset.

        Returns:
            bool: always True
        """

        if is_cron:
            complex_set = self.search(TRUE_DOMAIN)
            cron_domain = self._compute_cron_lastcall_domain()
        else:
            complex_set = self
            cron_domain = False

        if complex_set:
            template_xid = (
                "facility_management.mail_notify_reservation_requests"
            )
            mail_template = self.env.ref(template_xid)

            for record in complex_set:
                rows = record._compute_rows(cron_domain, filter_domain)

                if not rows:
                    continue

                context = record.env.context.copy()
                context.update(rows=rows)

                (
                    partner_set,
                    email_to_list,
                ) = record._compute_notify_requests_recipients()

                if not email_to_list:
                    continue

                email_values = {
                    "email_to": ", ".join(email_to_list),
                    "partner_ids": partner_set.ids,
                }

                context_template = mail_template.with_context(context)
                context_template.send_mail(
                    record.id, force_send=False, email_values=email_values
                )

        return True

    @api.model
    def _get_form_view_base_url(self, model, menu_xid):
        param = self.env["ir.config_parameter"]
        base_url = param.sudo().get_param("web.base.url")

        menu = self.env.ref(menu_xid)
        action = menu.action

        # Get top menu
        while menu.parent_id:
            menu = menu.parent_id

        url = "{}/web?#menu_id={}&action={}&model={}&view_type=form&id={{}}"
        return url.format(base_url, menu.id, action.id, model)

    def get_form_view_url(self):
        self.ensure_one()

        menu_xid = "facility_management.menu_facility_complex"
        base_url = self._get_form_view_base_url(self._name, menu_xid)

        return base_url.format(self.id)

    @staticmethod
    def format_email(recipient):
        """Format the email of the recipient with its name.

        Args:
            recipient (Model): Odoo model instance that has attributes name and
            email. This method is specilly designed to accept a res.partner, a
            res.users, or a res.company.

        Returns:
            str or False: Formatted email string as "Name <Email>", or just
            "Email" if name is not available. If recipient has no email,
            returns False.
        """

        if recipient and recipient.email:
            name = recipient.name
            email = recipient.email

            if name and len(name) >= 1:
                email_to = '"{}" <{}>'.format(name, email)
            else:
                email_to = email
        else:
            email_to = False

        return email_to

    def _compute_notify_requests_recipients(self):
        """Retrieve the email recipients for a given facility complex. This
        will be used to notify awaiting facility reservations.

        Recipients will be:
        1. Email of the partner and manager if specified and exists.
        2. Email of the company if specified and exists and and there were no
        emails for the partner or the manager.

        Returns:
            tuple: (res.partner recordset, list of "Name <Email>")
        """

        self.ensure_one()

        email_to_list = []
        partner_set = self.env["res.partner"]

        if self.partner_id and self.partner_id.email:
            partner_set |= self.partner_id
            email_to = self.format_email(partner_set)
            email_to_list.append(email_to)

        if self.manager_id and self.manager_id.email:
            partner_set |= self.manager_id.partner_id
            email_to = self.format_email(self.manager_id)
            email_to_list.append(email_to)

        if not email_to_list and self.company_id:
            if self.company_id.email:
                partner_set |= self.company_id.partner_id
                email_to = self.format_email(self.company_id)
                email_to_list.append(email_to)

            elif self.company_id.partner_id.email:
                partner_set |= self.company_id.partner_id
                email_to = self.format_email(self.company_id.partner_id)
                email_to_list.append(email_to)

        return partner_set, email_to_list
