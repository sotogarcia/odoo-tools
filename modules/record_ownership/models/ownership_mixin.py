# -*- coding: utf-8 -*-
###############################################################################
# License, author and contributors information in:                            #
# __manifest__.py file at the root folder of this module.                     #
###############################################################################

from odoo import models, fields, api
from odoo import SUPERUSER_ID
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
        copy=False,
    )

    def default_owner_id(self):
        """Compute the default owner for new records; this will be
        the current user or the root user.
        @note: root user will be used only for background actions.
        """
        return self.env.user or self.env.ref("base.user_root")

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
        copy=False,
    )

    # -- Computed field: manager_id -------------------------------------------

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
            value (mixed): the domain value to search for

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

    # -- Computed field: prerogative -------------------------------------------

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

        user = self.env.user

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

    # -- Overriden methods
    # -------------------------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        extra = ["tracking"]
        _super = super(OwnershipMixin, self)

        return name in extra or _super._valid_field_parameter(field, name)

    @api.model_create_multi
    def create(self, values_list):
        """Create records in batch (Odoo 18).
        - Enforce ownership rules per record prior to creation.
        - Subscribe owner/subrogate as followers after creation.
        """

        self._ensure_owner(values_list)
        self._sanitize_owner_subrogate_values(values_list)

        records = super(OwnershipMixin, self).create(values_list)
        records._fix_owner_subrogate_conflicts()  # belt and suspenders

        # records._subscribe_owner_and_subrogate()

        return records

    def write(self, values):
        """Prevent unauthorized users from changing ownership for others other
        than themselves.

        Appends owner/subrogate to mail.followers list.
        """

        self._sanitize_owner_subrogate_values(values)
        self._prevent_unauthorized_changes(values)

        result = super(OwnershipMixin, self).write(values)

        self._fix_owner_subrogate_conflicts()
        # self._subscribe_owner_and_subrogate()

        return result

    def copy(self, default=None):
        """Overridden copy: normalize owner and clear subrogate."""
        self.ensure_one()
        default = dict(default or {})

        # Always drop subrogation on copies
        default["subrogate_id"] = None

        # Enforce same rules as in create for owner/subrogate
        self._ensure_owner(default)
        self._sanitize_owner_subrogate_values(default)

        result = super(OwnershipMixin, self).copy(default)

        # Post-create: subscribe followers and fix conflicts
        result._fix_owner_subrogate_conflicts()
        # result._subscribe_owner_and_subrogate()

        return result

    # -- Auxiliary methods
    # -------------------------------------------------------------------------

    def _ensure_owner(self, values):
        """Normalize ownership-related fields on incoming values.

        Called from ``create``. Accepts a dict or a list of dicts
        (create-multi) and applies these rules:

        - If ``env.user`` is unavailable (rare), set ``owner_id`` to
          ``base.user_root`` (or ``SUPERUSER_ID``) and drop ``subrogate_id``.
        - If current user is not in the manager group
          (``record_ownership_manager``), force ``owner_id`` to current user.
        - If current user is in the manager group, keep provided
          ``owner_id`` or default it to current user.
        - If current user lacks the proxy group
          (``record_ownership_proxy``), drop ``subrogate_id``.

        Parameters
        ----------
        values : dict | list[dict]
            Values to normalize (mutated in place).

        Returns
        -------
        dict | list[dict]
            The same object received, after normalization, to ease chaining.
        """
        current_user = self.env.user

        manager_xid = "record_ownership.record_ownership_manager"
        is_manager = bool(current_user and current_user.has_group(manager_xid))

        proxy_xid = "record_ownership.record_ownership_proxy"
        has_proxy = bool(current_user and current_user.has_group(proxy_xid))

        def _fallback(vals):
            root = self.env.ref("base.user_root", raise_if_not_found=False)
            vals["owner_id"] = root.id if root else SUPERUSER_ID
            vals.pop("subrogate_id", None)

        def _apply(vals):
            assert isinstance(vals, dict), "'values' items must be dict"
            if not current_user or not getattr(current_user, "id", None):
                _fallback(vals)
                return
            if not is_manager or not vals.get("owner_id", False):
                vals["owner_id"] = current_user.id
            if not has_proxy:
                vals.pop("subrogate_id", None)

        if isinstance(values, list):
            for item in values:
                _apply(item)
        else:
            _apply(values)

        return values

    def _prevent_unauthorized_changes(self, values):
        """Remove forbidden ownership fields from given values dict.

        This method will be used in ``write`` method.

        Arguments:
            values {dict} -- dictionary with pairs field: value
        """
        current_user = self.env.user

        manager_xid = "record_ownership.record_ownership_manager"
        if not current_user.has_group(manager_xid):
            values.pop("owner_id", None)

        proxy_xid = "record_ownership.record_ownership_proxy"
        if not current_user.has_group(proxy_xid):
            values.pop("subrogate_id", None)

    @api.model
    def _sanitize_owner_subrogate_values(self, values):
        """Ensure ``owner_id`` and ``subrogate_id`` do not resolve to the same.

        Accepts a dict or a list of dicts (create/write payloads). If either
        ``owner_id`` or ``subrogate_id`` contains a recordset, it is coerced
        to its id (singleton or first record) before comparison. When both
        resolve to the same id, ``subrogate_id`` is cleared (set to ``None``).

        Mutates the incoming object in place and returns it to ease chaining
        with other normalizers.

        Parameters
        ----------
        values : dict | list[dict]
            Incoming values to sanitize.

        Returns
        -------
        dict | list[dict]
            The same object after sanitization.
        """

        def _apply(values):
            subrogate_id = values.get("subrogate_id", False)
            if not subrogate_id:
                return

            if isinstance(subrogate_id, models.BaseModel):
                subrogate_id = subrogate_id[:1].id

            owner_id = values.get("owner_id", False)
            if owner_id and isinstance(owner_id, models.BaseModel):
                owner_id = owner_id[:1].id

            if subrogate_id == owner_id:
                values["subrogate_id"] = None

        if isinstance(values, list):
            for item in values:
                _apply(item)
        else:
            _apply(values)

        return values

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

    def _inherit_from_mail_thread(self):
        has_field = "message_follower_ids" in self._fields
        has_method = callable(getattr(self, "message_subscribe", None))

        return has_field and has_method

    def _subscribe_owner_and_subrogate(self):
        """Subscribe owner_id and subrogate_id as followers when supported."""
        if not self._inherit_from_mail_thread():
            return

        for record in self:
            partner_ids = []

            owner = getattr(record, "owner_id", False)
            if owner and owner.partner_id:
                partner_ids.append(owner.partner_id.id)

            subrogate = getattr(record, "subrogate_id", False)
            if subrogate and subrogate.partner_id:
                partner_ids.append(subrogate.partner_id.id)

            if partner_ids:
                # Avoid unique constraint errors: add only non-followers
                existing = set(record.message_partner_ids.ids)
                to_add = [
                    pid for pid in set(partner_ids) if pid not in existing
                ]
                if to_add:
                    record.message_subscribe(partner_ids=to_add)

    # -- Legacy helpers (kept for backward compatibility)
    # -------------------------------------------------------------------------

    def _get_user(self, uid):
        """DEPRECATED: kept for compatibility. Prefer direct browse.

        Get res.users record related with given uid.

        Arguments:
            uid {int} -- ID of the owner to browse

        Returns:
            recordset -- single-item recordset with the user
        """

        _logger.debug("Deprecated: _get_user() called on %s", self._name)
        return self.env["res.users"].browse(uid)

    def _is_follower(self, user_item):
        """DEPRECATED: kept for compatibility. Prefer:
        ``partner in record.message_partner_ids``.

        Check whether the given user follows the current record.

         Arguments:
             user_item {recordset} -- res.users single-item recordset

         Returns:
              bool -- True if the given user follows the record
        """

        self.ensure_one()
        _logger.debug("Deprecated: _is_follower() called on %s", self._name)
        followers_obj = self.env["mail.followers"]

        domain = [
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("partner_id", "=", user_item.partner_id.id),
        ]

        return bool(followers_obj.search_count(domain))

    # -- Auto-subscription hook (mail.thread)
    # -------------------------------------------------------------------------

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        """Add owner/subrogate to auto-subscribe list (mail.thread hook).

        Return list of (partner_id, subtype_ids|False, qweb_template|False).
        Works on recordsets; relies only on `updated_values` like official
        addons (e.g., hr_expense).
        """
        # If the inheriting model is not an effective mail.thread, do nothing
        if not self._inherit_from_mail_thread():
            return []

        parent = super(OwnershipMixin, self)
        method = getattr(parent, "_message_auto_subscribe_followers", None)
        if not callable(method):
            return []

        result = method(updated_values, subtype_ids)

        # Act only when ownership fields are present in payload
        if (
            "owner_id" not in updated_values
            and "subrogate_id" not in updated_values
        ):
            return result

        owner_uid = updated_values.get("owner_id")
        subro_uid = updated_values.get("subrogate_id")

        # Normalize possible recordsets to ids
        if isinstance(owner_uid, models.BaseModel):
            owner_uid = owner_uid.id
        if isinstance(subro_uid, models.BaseModel):
            subro_uid = subro_uid.id

        if owner_uid:
            owner_user = self.env["res.users"].sudo().browse(owner_uid)
            if owner_user.exists() and owner_user.partner_id:
                result.append((owner_user.partner_id.id, subtype_ids, False))
        if subro_uid:
            subro_user = self.env["res.users"].sudo().browse(subro_uid)
            if subro_user.exists() and subro_user.partner_id:
                result.append((subro_user.partner_id.id, subtype_ids, False))

        return result

    # --- MRO sanity check ----------------------------------------------------
    # Why this exists
    # -----------------------------------------------------------------------------
    # Odoo's mail.thread triggers auto-subscription by calling
    # `self._message_auto_subscribe_followers(updated_values, subtype_ids)`.
    # In multiple inheritance, Python resolves which implementation to call
    # using the class MRO (C3 linearization): the *first* implementation found
    # wins. If a model inherits both `ownership.mixin` and `mail.thread` but
    # lists `mail.thread` before `ownership.mixin` in `_inherit`, the MRO will
    # place `MailThread` before `OwnershipMixin`. As a result, our override
    # `_message_auto_subscribe_followers` will NOT be called and
    # owner/subrogate will not be auto-subscribed via the hook.
    #
    # I could have a manual fallback (safe, deduped `message_subscribe`) in
    # create/write/copy, but I preferred to let the mail.thread's hook
    # do the job to stay aligned with Odoo’s native flow and other addons.
    #
    # What the check does
    # -----------------------------------------------------------------------------
    # During `_setup_complete()` we inspect the model class MRO and WARN when
    # `OwnershipMixin` appears *after* `MailThread`. This is a non-fatal
    # warning intended for developers; it does not change runtime behavior.
    # If the `mail` module is not installed, the check is skipped.
    #
    # How to fix the warning
    # -----------------------------------------------------------------------------
    # Reorder the `_inherit` so that `ownership.mixin` comes BEFORE
    # `mail.thread`, e.g.:
    #
    #   _inherit = ['ownership.mixin', 'mail.thread', 'mail.activity.mixin']
    #
    # If reordering is not possible for a specific model, define a small
    # override on that model and append owner/subrogate partners there, e.g.:
    #
    #   def _message_auto_subscribe_followers(self, vals, subtype_ids):
    #       res = super()._message_auto_subscribe_followers(vals, subtype_ids)
    #       # add owner/subrogate partners (same logic as the mixin)
    #       return res
    #
    # Notes / edge cases
    # -----------------------------------------------------------------------------
    # - The warning is informational; behavior is unchanged if you ignore it.
    # - Context flags `mail_create_nosubscribe` / `mail_update_nosubscribe`
    #   can still bypass auto-subscription even with a correct MRO order.
    # - If other addons override the same hook, they MUST call `super()` so
    #   behaviors compose correctly along the MRO chain.

    def _check_mail_thread_mro_order(self):
        """Warn if OwnershipMixin appears after mail.thread in the MRO.
        In that case, our _message_auto_subscribe_followers override
        no será llamado por mail.thread.
        """
        try:
            from odoo.addons.mail.models.mail_thread import MailThread
        except Exception:
            return  # 'mail' not installed / not relevant

        cls = type(self)
        mro = cls.mro()
        if MailThread in mro and OwnershipMixin in mro:
            if mro.index(OwnershipMixin) > mro.index(MailThread):
                _logger.warning(
                    "ownership.mixin should precede mail.thread in _inherit "
                    "for model %s to enable auto-subscribe hook. Current MRO: %s",
                    self._name,
                    " -> ".join(c.__name__ for c in mro[:20]),
                )

    def _setup_complete(self):
        res = super(OwnershipMixin, self)._setup_complete()
        # Ejecuta la comprobación para cada modelo que incluya el mixin
        self._check_mail_thread_mro_order()
        return res
