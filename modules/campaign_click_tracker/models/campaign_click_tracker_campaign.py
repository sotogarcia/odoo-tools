# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.osv.expression import FALSE_DOMAIN
from odoo.tools import safe_eval

from logging import getLogger
from uuid import uuid4


_logger = getLogger(__name__)


class CampaignClickTrackerCampaign(models.Model):
    """
    Defines a campaign with its description, available answers,
    and user input records.
    """

    _name = 'campaign.click.tracker.campaign'
    _description = u'Campaign click tracker campaign'

    _inherit = ['mail.thread']

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Name of the campaign shown to users',
        translate=True,
        track_visibility='onchange',
        copy=False
    )

    active = fields.Boolean(
        string='Active',
        required=False,
        readonly=False,
        index=True,
        default=True,
        help='Check to activate this campaign',
        track_visibility='onchange'
    )

    description = fields.Text(
        string='Description',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Optional description or context for the campaign',
        translate=True
    )

    available_answer_ids = fields.One2many(
        string='Options',
        required=True,
        readonly=False,
        default=None,
        help='Available answer options for this campaign',
        comodel_name='campaign.click.tracker.answer',
        inverse_name='campaign_id',
        domain=[],
        context={},
        auto_join=False,
        limit=None
    )

    available_answer_count = fields.Integer(
        string='Option count',
        required=False,
        readonly=True,
        index=False,
        default=0,
        help='Number of answer options in this campaign',
        compute='_compute_available_answer_count',
        search='_search_available_answer_count',
        copy=False
    )

    @api.depends('available_answer_ids')
    def _compute_available_answer_count(self):
        for record in self:
            record.available_answer_count = len(record.available_answer_ids)

    @api.model
    def _search_available_answer_count(self, operator, value):

        if isinstance(value, bool) or value is None:
            if operator == '=':
                operator = '>' if value else '<='
            else:
                operator = '>' if not value else '<='
            value = 0

        sql = '''
            SELECT 
                campaign_id
            FROM
                campaign_click_tracker_answer AS ta
            WHERE active IS TRUE
            GROUP BY campaign_id
            HAVING count("id") {operator} {value}
        '''.format(operator=operator, value=value)

        cursor = self.env.cr
        cursor.execute(sql)
        results = cursor.dictfetchall()

        if results:
            campaign_ids = [item['campaign_id'] for item in results]
            return [('id', 'in', campaign_ids)]

        return FALSE_DOMAIN

    user_input_ids = fields.One2many(
        string='User inputs',
        required=True,
        readonly=False,
        default=None,
        help='User responses associated with this campaign',
        comodel_name='campaign.click.tracker.user.input',
        inverse_name='campaign_id',
        domain=[],
        context={},
        auto_join=False,
        limit=None
    )

    user_input_count = fields.Integer(
        string='User input count',
        required=False,
        readonly=True,
        index=False,
        default=0,
        help='Number of user responses registered in this campaign',
        compute='_compute_user_input_count',
        search='_search_user_input_count',
        copy=False
    )

    @api.depends('user_input_ids')
    def _compute_user_input_count(self):
        for record in self:
            record.user_input_count = len(record.user_input_ids)

    @api.model
    def _search_user_input_count(self, operator, value):

        if isinstance(value, bool) or value is None:
            if operator == '=':
                operator = '>' if value else '<='
            else:
                operator = '>' if not value else '<='
            value = 0

        sql = '''
            SELECT 
                campaign_id
            FROM
                campaign_click_tracker_user_input AS ui
            WHERE active IS TRUE
            GROUP BY campaign_id
            HAVING count("id") {operator} {value}
        '''.format(operator=operator, value=value)

        cursor = self.env.cr
        cursor.execute(sql)
        results = cursor.dictfetchall()

        if results:
            campaign_ids = [item['campaign_id'] for item in results]
            return [('id', 'in', campaign_ids)]

        return FALSE_DOMAIN

    partner_count = fields.Integer(
        string='Partner count',
        required=False,
        readonly=True,
        index=False,
        default=0,
        help='Number of unique partners with input records in this campaign',
        compute='_compute_partner_count' ,
        copy=False
    )

    @api.depends('user_input_ids', 'user_input_ids.partner_id')
    def _compute_partner_count(self):
        for record in self:
            record.partner_count = len(
                set(record.user_input_ids.mapped('partner_id.id'))
            )

    answered_count = fields.Integer(
        string='Answered count',
        required=False,
        readonly=True,
        index=False,
        default=0,
        help='Number of user inputs with a selected answer in this campaign',
        compute='_compute_answered_count',
        copy=False
    )

    @api.depends('user_input_ids', 'user_input_ids.answer_id')
    def _compute_answered_count(self):
        for record in self:
            record.answered_count = len(
                record.user_input_ids.filtered(lambda r: r.answer_id)
            )

    def view_user_inputs(self):
        self.ensure_one()
    
        action_xid = 'campaign_click_tracker.action_user_input_act_window'
        act_wnd = self.env.ref(action_xid)
    
        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))
        context.update({'default_campaign_id': self.id})
    
        domain = [('campaign_id', '=', self.id)]
    
        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': act_wnd.res_model,
            'target': 'current',
            'name': act_wnd.name,
            'view_mode': act_wnd.view_mode,
            'domain': domain,
            'context': context,
            'search_view_id': act_wnd.search_view_id.id,
            'help': act_wnd.help
        }
    
        return serialized

    _sql_constraints = [
        (
            'unique_name',
            'UNIQUE(name)',
            _('The campaign name must be unique.')
        )
    ]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """
            Create a new record in CampaignClickTrackerCampaign model from existing one
            @param default: dict which contains the values to be override
            during copy of object
    
            @return: returns a id of newly created record
        """
    
        default = dict(default or {})

        name = default.get('name', False)
        if not name:
            name = f'{self.name} - {str(uuid4())[-12:]}'
            default['name'] = name

        parent = super(CampaignClickTrackerCampaign, self)
        result = parent.copy(default)
    
        if self.available_answer_ids:
            answer_values = {'campaign_id': result.id}
            for answer in self.available_answer_ids:
                answer_values.update(name=answer.name)
                answer.copy(answer_values)

        if self.user_input_ids:
            user_input_values = {'campaign_id': result.id}
            for user_input in self.user_input_ids:
                user_input_values.update(partner_id=user_input.partner_id.id)
                user_input.copy(user_input_values)

        return result


