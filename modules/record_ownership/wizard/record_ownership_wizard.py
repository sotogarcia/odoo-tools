# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger
from odoo.osv.expression import AND, FALSE_LEAF, FALSE_DOMAIN, TRUE_DOMAIN
from odoo.exceptions import UserError

_logger = getLogger(__name__)


class RecordOwnershipWizard(models.TransientModel):
    """
    """

    _name = 'record.ownership.wizard'
    _description = u'Record ownership wizard'

    _rec_name = 'id'
    _order = 'id DESC'

    model_id = fields.Many2one(
        string='Model',
        required=True,
        readonly=True,
        index=False,
        default=lambda self: self.default_model_id(),
        help='Target model',
        comodel_name='ir.model',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    def default_model_id(self):
        model_set = self.env['ir.model']

        active_model = self.env.context.get('active_model', False)
        if active_model:
            domain = [('model', '=', active_model)]
            model_set = model_set.search(domain, limit=1)

        return model_set

    record_count = fields.Integer(
        string='Record count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Total number of selected records',
        compute='_compute_record_count'
    )

    @api.depends('model_id')
    @api.depends_context('active_model', 'active_ids', 'active_id')
    def _compute_record_count(self):
        active_ids = self.get_active_ids()

        for record in self:
            if record.model_id and active_ids:
                domain = [('id', 'in', active_ids)]
                model_obj = self.env[record.model_id.model]
                record.record_count = model_obj.search_count(domain)
            else:
                record.record_count = 0

    change_owner = fields.Boolean(
        string='Change owner',
        required=False,
        readonly=False,
        index=False,
        default=False,
        help='Check it to establish owner'
    )

    owner_id = fields.Many2one(
        string='Owner',
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.env.user,
        help='Select the user to appear as the owner',
        comodel_name='res.users',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    change_subrogate = fields.Boolean(
        string='Change subrogate',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='Check it to establish surrogacy'
    )

    subrogate_id = fields.Many2one(
        string='Subrogate',
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.env.user,
        help='Select the user to which the records will be subrogated',
        comodel_name='res.users',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    target_count = fields.Integer(
        string='Target count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Number of target records',
        compute='_compute_target_count'
    )

    @api.depends('change_owner', 'owner_id', 'change_subrogate',
                 'subrogate_id')
    @api.depends_context('active_model', 'active_ids', 'active_id')
    def _compute_target_count(self):
        for record in self:
            model_id = record.model_id

            if model_id and self._change_was_indicated():
                domain = record.build_target_domain()

                model_obj = self.env[record.model_id.model]
                record.target_count = model_obj.search_count(domain)

            else:
                record.target_count = 0

    fix_redundancy = fields.Selection(
        string='Fix redundancy',
        required=True,
        readonly=False,
        index=False,
        default='ch',
        help='Choose it to correct delegations to the owner himself',
        selection=[
            ('no', 'No'),
            ('tg', 'Target records'),
            ('ch', 'Chosen records'),
            ('db', 'All the records')
        ]
    )

    tracking_disable = fields.Boolean(
        string='Tracking disable',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='Disable tracking'
    )

    def _change_was_indicated(self):
        self.ensure_one()

        return self.change_owner or self.change_subrogate

    @api.model
    def get_active_ids(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            active_id = self.env.context.get('active_id', None)
            if active_id:
                active_ids = [active_id]

        return active_ids

    def _build_records_domain(self):
        self.ensure_one()

        active_ids = self.get_active_ids()

        return [('id', 'in', active_ids)] if active_ids else FALSE_DOMAIN

    def _build_property_domain(self):
        self.ensure_one()

        if self.change_owner and self.owner_id:
            owner_leaf = ('owner_id', '!=', self.owner_id.id)
        else:
            owner_leaf = FALSE_LEAF

        if self.change_subrogate and self.subrogate_id:
            subrogate_leaf = ('subrogate_id', '!=', self.subrogate_id.id)
        else:
            subrogate_leaf = FALSE_LEAF

        return ['|', owner_leaf, subrogate_leaf]

    def build_target_domain(self):
        records_domain = self._build_records_domain()
        property_domain = self._build_property_domain()

        return AND([records_domain, property_domain])

    def _build_values(self):
        self.ensure_one()

        values = {}

        if self.change_owner and self.owner_id:
            values['owner_id'] = self.owner_id.id

        if self.change_subrogate and self.subrogate_id:
            values['subrogate_id'] = self.subrogate_id.id

        return values

    def _update_ownership(self):
        self.ensure_one()

        model = self.model_id.model
        model_obj = self.env[model]
        domain = self.build_target_domain()
        model_set = model_obj.search(domain)

        values = self._build_values()
        if model_set and values:
            model_set.write(values)

    def _fix_redundancy(self):
        self.ensure_one()

        def is_redundant(record):
            return record.owner_id == record.subrogate_id

        if self.fix_redundancy != 'no':

            domain = [('subrogate_id', '!=', False)]

            if self.fix_redundancy == 'tg':  # Target
                target_domain = self.build_target_domain()
                domain = AND([domain, target_domain])

            elif self.fix_redundancy == 'ch':  # Chosen
                active_ids = self.get_active_ids()
                active_domain = [('id', 'in', active_ids)]
                domain = AND([domain, active_domain])

            elif self.fix_redundancy == 'db':  # All in the database
                pass

            else:
                raise UserError(_('Invalid value in fix_redundancy field'))

            model = self.model_id.model
            model_obj = self.env[model]
            model_set = model_obj.search(domain)

            model_set = model_set.filtered(lambda r: is_redundant(r))
            model_set.write({'subrogate_id': False})

    def _perform_action(self):
        self.ensure_one()

        if self.tracking_disable:
            tracking_disable_ctx = self.env.context.copy()
            tracking_disable_ctx.update({'tracking_disable': True})
            self = self.with_context(tracking_disable_ctx)

        self._update_ownership()
        self._fix_redundancy()

    def perform_action(self):
        msg = _('The operation could not be completed. The system says: {}')

        self.env.cr.autocommit(False)

        try:

            for record in self:
                self._perform_action()

            self.env.cr.commit()

        except Exception as ex:
            _logger.error(ex)
            raise UserError(msg.format(ex))

        finally:
            self.env.cr.autocommit(True)
