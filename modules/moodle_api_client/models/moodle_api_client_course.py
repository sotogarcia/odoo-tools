# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import safe_eval
from odoo.tools.translate import _

from logging import getLogger

_logger = getLogger(__name__)


class MoodleApiClientCourse(models.Model):

    _name = 'moodle.api.client.course'
    _description = u'Moodle api client course'

    _rec_name = 'name'
    _order = 'write_date DESC, name ASC'

    _inherit = ['mail.thread', 'moodle.api.client.base']

    # fullname --> name
    # id --> moodleid

    shortname = fields.Char(
        string='Shortname',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help=False,
        translate=False
    )

    summary = fields.Text(
        string='Summary',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help=False,
        translate=False
    )

    summaryformat = fields.Selection(
        string='Message Format',
        required=True,
        readonly=True,  # Not available yet
        index=False,
        default='1',
        help='Format of the message content',
        selection=[
            ('0', 'Plain Text'),
            ('1', 'HTML'),
        ]
    )

    startdate = fields.Datetime(
        string='Start Date',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='Course start date in local time'
    )

    enddate = fields.Datetime(
        string='End Date',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='Course end date in local time'
    )

    visible = fields.Boolean(
        string='Visible',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help=False
    )

    forum_ids = fields.One2many(
        string='Forums',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help=False,
        comodel_name='moodle.api.client.forum',
        inverse_name='course_id',
        domain=[],
        context={},
        auto_join=False,
        limit=None
    )

    # - Field: forum_count (compute)
    # ------------------------------------------------------------------------

    forum_count = fields.Integer(
        string='Forum count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help=False,
        compute='_compute_forum_count'
    )

    @api.depends('forum_ids')
    def _compute_forum_count(self):
        for record in self:
            record.forum_count = len(record.forum_ids)

    # -------------------------------------------------------------------------
    # PUBLIC METHODS
    # -------------------------------------------------------------------------

    def view_forums(self):
        self.ensure_one()
    
        action_xid = 'moodle_api_client.action_moodle_forum_act_window'
        act_wnd = self.env.ref(action_xid)
    
        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))
        context.update({'default_course_id': self.id})
    
        domain = [('course_id', '=', self.id)]
    
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
