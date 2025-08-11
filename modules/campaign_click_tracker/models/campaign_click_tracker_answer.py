# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _

from logging import getLogger
from uuid import uuid4

_logger = getLogger(__name__)


class CampaignClickTrackerAnswer(models.Model):
    """
    Defines an answer option available in a campaign.
    Each answer has a unique token and a translatable label.
    """

    _name = 'campaign.click.tracker.answer'
    _description = u'Campaign click tracker answer'

    _inherit = ['mail.thread']

    _rec_name = 'name'
    _order = 'name ASC'

    token = fields.Char(
        string='Token',
        required=True,
        readonly=True,
        index=True,
        default=lambda self: str(uuid4()),
        help='Unique token used to track this answer',
        translate=False,
        copy=False,
        track_visibility='always'
    )

    name = fields.Char(
        string='Name',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Name of the answer displayed to users',
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
        help='Check to activate this answer',
        track_visibility='onchange'
    )

    description = fields.Text(
        string='Description',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Optional description or details',
        translate=True
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

    _sql_constraints = [
        (
            'unique_answer_token',
            'UNIQUE(token)',
            _('The token must be unique.')
        ),
        (
            'unique_campaign_name',
            'UNIQUE(campaign_id, name)',
            _('Each answer must have a unique name within the same campaign.')
        )
    ]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """
            Create a new record in ModelName model from existing one
            @param default: dict which contains the values to be override
            during copy of object
    
            @return: returns a id of newly created record
        """
    
        default = dict(default or {})

        name = default.get('name', False)
        if not name:
            name = f'{self.name} - {str(uuid4())[-12:]}'
            default['name'] = name

        parent = super(CampaignClickTrackerAnswer, self)
        result = parent.copy(default)
    
        return result
    
