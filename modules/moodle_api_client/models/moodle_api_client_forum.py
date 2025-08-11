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


class MoodleApiClientForum(models.Model):

    _name = 'moodle.api.client.forum'
    _description = u'Moodle api client forum'

    _rec_name = 'name'
    _order = 'write_date DESC, name ASC'

    _inherit = ['mail.thread', 'moodle.api.client.base']

    course_id = fields.Many2one(
        string='Course',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help=False,
        comodel_name='moodle.api.client.course',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    discussion_ids = fields.One2many(
        string='Discussions',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help=False,
        comodel_name='moodle.api.client.discussion',
        inverse_name='forum_id',
        domain=[],
        context={},
        auto_join=False,
        limit=None
    )

    # - Field: discussion_count (compute)
    # ------------------------------------------------------------------------

    discussion_count = fields.Integer(
        string='Discussion count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help=False,
        compute='_compute_discussion_count'
    )

    @api.depends('discussion_ids')
    def _compute_discussion_count(self):
        for record in self:
            record.discussion_count = len(record.discussion_ids)

    # -------------------------------------------------------------------------
    # PUBLIC METHODS
    # -------------------------------------------------------------------------

    def view_discussions(self):
        self.ensure_one()
    
        action_xid = 'moodle_api_client.action_moodle_discussion_act_window'
        act_wnd = self.env.ref(action_xid)
        
        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))
        context.update({
            'default_forum_id': self.id,
            'default_platform_id': self.platform_id.id,
            'default_user_id': self.user_id.id
        })
    
        domain = [('forum_id', '=', self.id)]
    
        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': act_wnd.res_model,
            'target': 'current',
            'name': _('Discussions'),
            'view_mode': act_wnd.view_mode,
            'domain': domain,
            'context': context,
            'search_view_id': act_wnd.search_view_id.id,
            'help': act_wnd.help
        }
    
        return serialized

    def synchronize_discussions(self):
        for record in self:
            record._synchronize_discussions()

    def _synchronize_discussions(self):
        """Finds a Moodle discussion by discussion ID or moodleid"""
        self.ensure_one()

        discussion_obj = self.env['moodle.api.client.discussion']

        driver = self.platform_id._get_driver()
        function = 'mod_forum_get_forum_discussions_paginated'
        
        page = 0
        perpage = 20  # Use maximum allowed if known

        while True:
            params = {
                'forumid': self.moodleid,
                'page': page,
                'perpage': perpage
            }
            response = driver.call(function, params)
            discussions = response.get('discussions', [])

            if not discussions:
                break

            for discussion in discussions:
                moodleid = discussion.get('id')

                values = {
                    'forum_id': self.id,
                    'platform_id': self.platform_id.id,
                    'user_id': self.user_id.id,
                    'groupid': discussion.get('groupid'),
                    'name': discussion.get('subject'),
                    'content': discussion.get('message'),
                    'discussionid': discussion.get('discussion')
                }

                discussion_record = self.discussion_ids.filtered(
                    lambda d: d.moodleid == moodleid
                )

                if discussion_record:
                    discussion_record = discussion_record[0]
                    discussion_record.write(values)
                else:
                    values['moodleid'] = moodleid
                    discussion_obj.create(values)

            page += 1

        return None
