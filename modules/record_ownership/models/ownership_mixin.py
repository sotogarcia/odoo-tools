# -*- coding: utf-8 -*-
###############################################################################
# License, author and contributors information in:                            #
# __manifest__.py file at the root folder of this module.                     #
###############################################################################

from odoo import models, fields, api

from logging import getLogger

# pylint: disable=locally-disabled, C0103
_logger = getLogger(__name__)


# pylint: disable=locally-disabled, R0903,W0212
class OwnershipMixin(models.AbstractModel):
    """Models can extend this to touch related models through 'x2many' fields"""

    _name = "ownership.mixin"

    _description = "Provides owner field and behavior"

    _min_group_allowed = "record_ownership.record_ownership_manager"

    owner_id = fields.Many2one(
        string="Owner",
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.default_owner_id(),
        help="Current record owner",
        comodel_name="res.users",
        domain=[],
        context={},
        ondelete="restrict",
        auto_join=False,
        groups="record_ownership.record_ownership_consultant",
        tracking=True,
    )

    subrogate_id = fields.Many2one(
        string="Subrogate",
        required=False,
        readonly=False,
        index=True,
        default=None,
        help="Person who assumes the obligations of the owner",
        comodel_name="res.users",
        domain=[],
        context={},
        ondelete="set null",
        auto_join=False,
        groups="record_ownership.record_ownership_consultant",
        tracking=True,
    )

    manager_id = fields.Many2one(
        string="Manager",
        required=False,
        readonly=True,
        index=False,
        default=None,
        help="Person in charge of this record",
        comodel_name="res.users",
        domain=[],
        context={},
        ondelete="no action",
        auto_join=False,
        compute="_compute_manager_id",
        search="_search_manager_id",
        groups="record_ownership.record_ownership_consultant",
        store=False,
    )

    @api.depends("owner_id", "subrogate_id")
    def _compute_manager_id(self):
        for record in self:
            origin = record.sudo()
            record.manager_id = origin.subrogate_id or origin.owner_id

    @api.model
    def _search_manager_id(self, operator, value):
        """ Allow to search by person in charge, this person can be the
        the record owner or other subrogate user

        ```
        subrogate_id ? value | (subrogate_id = None & owner_id ? value)

                             |
                            / \
        subrogate_id ? value   &
                              / \
            subrogate_id = None  owner_id ? value

        |, subrogate_id ? value, &, subrogate_id = None & owner_id ? value
        ```

        Args:
            operator (str): domain leaf operator
            value (mided): the domain value to search for

        Returns:
            list: valid Odoo domain to search by person in charge
        """

        return [
            "|",
            ("subrogate_id", operator, value),
            "&",
            ("subrogate_id", "=", False),
            ("owner_id", operator, value),
        ]

    prerogative = fields.Selection(
        string="Prerogative",
        required=True,
        readonly=True,
        index=False,
        default="0",
        help="Compute current user access rights to change authorship",
        selection=[
            ("0", "Forbidden"),
            ("1", "Consultant"),
            ("2", "Proxy"),
            ("3", "Manager"),
        ],
        store=False,
        compute="_compute_prerogative",
    )

    @api.depends("owner_id", "subrogate_id")
    @api.depends_context("uid")
    def _compute_prerogative(self):
        """Compute current user access rights to change authorship. This will
        be used to enable or disable fields in related views.
        """

        uid = self.env.context.get("uid", False)
        user = self.env["res.users"].browse(uid)

        if user.has_group("record_ownership.record_ownership_manager"):
            prerogative = "3"
        elif user.has_group("record_ownership.record_ownership_proxy"):
            prerogative = "2"
        elif user.has_group("record_ownership.record_ownership_consultant"):
            prerogative = "1"
        else:
            prerogative = False

        for record in self:
            record.prerogative = prerogative

    def _valid_field_parameter(self, field, name):
        extra = ["tracking"]
        _super = super(OwnershipMixin, self)

        return name in extra or _super._valid_field_parameter(field, name)

    def default_owner_id(self):
        """Compute the default owner for new questions; this will be
        the current user or the root user.
        @note: root user will be used only for background actions.
        """
        uid = self.env.context.get("uid", False)
        if not uid:
            uid = self.env.ref("base.user_root").id

        return uid

    def _get_user(self, uid):
        """Get res.users model related with given uid

        Arguments:
            uid {int} -- ID of the owner to which user will be browse

        Returns:
            recordset -- single item recorset with the user
        """

        return self.env["res.users"].browse(uid)

    def _is_follower(self, user_item):
        """Check if given user is follows current self (single) record

        Arguments:
            user_item {recordset} -- res.users single item recordset

        Returns:
            bool -- True if given user follows self (single) record
        """

        followers_obj = self.env["mail.followers"]

        domain = [
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("partner_id", "=", user_item.partner_id.id),
        ]

        return bool(followers_obj.search_count(domain))

    def _ensure_owner(self, values):
        """Appends current user as owner_id in given values dictionary

        This method will be used in ``create`` method

        Arguments:
            values {dict} -- dictionary with pairs field: value
        """

        user = self.env["res.users"]
        uid = self.env.context.get("uid", False)
        if uid:
            user = user.browse(uid)

        manager_xid = "record_ownership.record_ownership_manager"
        if not user or not user.has_group(manager_xid):
            if uid:
                values["owner_id"] = uid
            else:
                root_user = self.env.ref("base.user_root")
                values["owner_id"] = root_user.id

        proxy_xid = "record_ownership.record_ownership_proxy"
        if not user or not user.has_group(proxy_xid):
            values.pop("subrogate_id", False)

    def _prevent_unauthorized_changes(self, values):
        """Removes ``owner_id`` key and value from given values dictionary

        This method will be used in ``write`` method

        Arguments:
            values {dict} -- dictionary with pairs field: value
        """

        manager_xid = "record_ownership.record_ownership_manager"
        proxy_xid = "record_ownership.record_ownership_proxy"

        current_user = uid = self.env.user
        if not current_user.has_group(manager_xid):
            values.pop("owner_id", False)

        if not current_user.has_group(proxy_xid):
            values.pop("subrogate_id", False)

    @api.model
    def _sanitize_owner_subrogate_values(self, values):
        subrogate_id = values.get("subrogate_id", False)

        if subrogate_id and subrogate_id == values.get("owner_id", False):
            values["subrogate_id"] = None

    def _fix_owner_subrogate_conflicts(self):
        """Clear subrogate when it equals owner for current records."""
        bad = self.filtered(
            lambda r: r.owner_id
            and r.subrogate_id
            and r.owner_id == r.subrogate_id
        )
        if bad:
            _logger.info(
                "Clearing subrogate for %d record(s): %s",
                len(bad),
                ",".join(map(str, bad.ids)),
            )
            bad.write({"subrogate_id": False})

    def _ensure_managers_as_followers(self, values):
        """Suscribes given user to all the records in given recordset.
        This method check if ``message_subscribe`` method exists
        """

        current_partner = self.env.user.partner_id
        if "mail.thread" in self._inherit:
            for record in self:
                subscribe = getattr(record.sudo(), "message_subscribe")

                if (
                    "owner_id" in values.keys()
                    and record.owner_id
                    and record.owner_id.partner_id != current_partner
                ):
                    subscribe([record.owner_id.partner_id.id])

                if (
                    "subrogate_id" in values.keys()
                    and record.subrogate_id
                    and record.subrogate_id.partner_id != current_partner
                ):
                    subscribe(partner_ids=[record.subrogate_id.partner_id.id])

    @api.model_create_multi
    def create(self, vals_list):
        """Create records in batch (Odoo 18).
        - Enforce ownership rules per record prior to creation.
        - Subscribe managers/followers after creation.
        """
        # Pre-create: enforce owner/subrogate for each item

        for values in vals_list:
            self._ensure_owner(values)
            self._sanitize_owner_subrogate_values(values)

        records = super(OwnershipMixin, self).create(vals_list)

        # Post-create: ensure followers per created record
        for rec, values in zip(records, vals_list):
            rec._ensure_managers_as_followers(values)

        return records

    def write(self, values):
        """Prevent unauthorized users from changing ownership for others other
        than themselves.

        Appends owner to mail.followers list.
        """

        self._sanitize_owner_subrogate_values(values)
        self._prevent_unauthorized_changes(values)

        result = super(OwnershipMixin, self).write(values)

        self._fix_owner_subrogate_conflicts()
        self._ensure_managers_as_followers(values)

        return result
