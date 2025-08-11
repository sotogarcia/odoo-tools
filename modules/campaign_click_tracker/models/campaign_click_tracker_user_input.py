# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.osv.expression import FALSE_DOMAIN

from logging import getLogger
from uuid import uuid4


_logger = getLogger(__name__)


class CampaignClickTrackerUserInput(models.Model):
    """
    Stores a partner"s participation in a campaign,
    identified by a unique token.
    """

    _name = 'campaign.click.tracker.user.input'
    _description = u'Campaign click tracker user input'

    _inherit = ['mail.thread']

    _rec_name = 'name'
    _order = 'name ASC'

    token = fields.Char(
        string='Token',
        required=True,
        readonly=True,
        index=True,
        default=lambda self: str(uuid4()),
        help='Unique token to identify this user input',
        translate=False,
        copy=False,
        track_visibility='always'
    )

    campaign_id = fields.Many2one(
        string='Campaign',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Campaign to which this response belongs',
        comodel_name='campaign.click.tracker.campaign',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False,
        track_visibility='onchange'
    )

    partner_id = fields.Many2one(
        string='Partner',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Partner associated with this campaign input',
        comodel_name='res.partner',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False,
        track_visibility='onchange',
        copy=False
    )

    name = fields.Char(
        string='Name',
        readonly=True,
        index=True,
        default=None,
        help='Partner name (copied from contact)',
        related='partner_id.name',
        store=True,
        copy=False
    )

    email = fields.Char(
        string='Email',
        readonly=True,
        index=True,
        default=None,
        help='Partner email (copied from contact)',
        related='partner_id.email',
        store=True,
        copy=False
    )

    active = fields.Boolean(
        string='Active',
        required=False,
        readonly=False,
        index=True,
        default=True,
        help='Check to enable this user input',
        track_visibility='onchange'
    )

    answer_id = fields.Many2one(
        string='Answer',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='Answer selected by the partner',
        comodel_name='campaign.click.tracker.answer',
        domain=[],
        context={},
        ondelete='set null',
        auto_join=False,
        track_visibility='onchange',
        copy=False
    )

    @api.onchange('campaign_id')
    def _onchange_campaign_id(self):
        if self.campaign_id:
            domain = [('campaign_id', '=', self.campaign_id.id)]
        else:
            domain = FALSE_DOMAIN

        return {
            'domain': {
                'answer_id': domain
            }
        }

    extra = fields.Char(
        string='Extra',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help=('Differentiator for multiple responses from the same user in '
              'the same campaign'),
        translate=False,
        track_visibility='onchange'
    )

    comment = fields.Text(
        string='Comment',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Optional user comment for this response.',
        translate=False,
        track_visibility='onchange'
    )

    _sql_constraints = [
        (
            'unique_user_input_token',
            'UNIQUE(token)',
            'The token must be unique.'
        ),
        (
            'unique_user_campaign_extra',
            'UNIQUE(partner_id, campaign_id, extra)',
            'Each user can only have one input per campaign and extra value.'
        )
    ]

    @api.constrains('campaign_id', 'answer_id')
    def _check_answer_id(self):
        for record in self:
            valid_answers = record.campaign_id.available_answer_ids

            if record.answer_id and record.answer_id not in valid_answers:
                campaign_name = record.campaign_id.display_name
                answer_name = record.answer_id.display_name
                
                raise ValidationError(_(
                    "Answer '%s' is not valid for campaign '%s'."
                ) % (answer_name, campaign_name))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """
            Create a new record in CampaignClickTrackerUserInput model from existing one
            @param default: dict which contains the values to be override
            during copy of object
    
            @return: returns a id of newly created record
        """
    
        default = dict(default or {})

        if not 'partner_id' in default:
            user = self.env.user or self.env.ref('base.user_root')
            default['partner_id'] = user.partner_id.id

        parent = super(CampaignClickTrackerUserInput, self)
        result = parent.copy(default)
    
        return result
    

