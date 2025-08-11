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


class MoodleApiClientDiscussion(models.Model):

    _name = 'moodle.api.client.discussion'
    _description = u'Moodle api client discussion'

    _rec_name = 'name'
    _order = 'write_date DESC, name ASC'

    _inherit = ['mail.thread', 'moodle.api.client.base']

    forum_id = fields.Many2one(
        string='Forum',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help=False,
        comodel_name='moodle.api.client.forum',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    forumid = fields.Integer(
        string='Forum ID',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='ID of the forum in Moodle where this discussion belongs',
        related='forum_id.moodleid'
    )

    discussionid = fields.Integer(
        string='Discussion ID',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='Moodle discussion ID returned when the discussion is created'
    )

    content = fields.Html(
        string='Content',
        required=True,
        readonly=False,
        index=False,
        default=None,
        help='Initial post message of the discussion thread',
    )

    content_format = fields.Selection(
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

    groupid = fields.Integer(
        string='Group ID',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help=('Optional group ID for posting the discussion to a specific '
              'group within the forum')
    )

    discussionsubscribe = fields.Selection(
        string='Discussion Subscribe',
        required=False,
        readonly=False,
        index=False,
        default=None,
        selection=[('1', 'Yes'), ('0', 'No')],
        help=('If enabled, the user will be subscribed to the discussion and '
              'receive notifications')
    )

    # - Field: content_length (compute)
    # ------------------------------------------------------------------------

    content_length = fields.Integer(
        string='Length',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Total number of characters in the page content',
        compute='_compute_content_length'
    )

    @api.depends('content')
    def _compute_content_length(self):
        for record in self:
            record.content_length = len(record.content or '')

    # - Field: user_id (default)
    # ------------------------------------------------------------------------

    user_id = fields.Many2one(
        string='Author',
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self._default_user_id(),
        help='User who created the discussion',
        comodel_name='res.users',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    def _default_user_id(self):
        try:
            return self.env.user.id or self.env.ref('base.user_root').id
        except Exception:
            return 1  # fallback to superuser ID in case of unexpected errors

    # -------------------------------------------------------------------------
    # PUBLIC METHODS
    # -------------------------------------------------------------------------

    def view_discussion_posts(self):
        self.ensure_one()
    
        action_xid = 'moodle_api_client.action_moodle_discussion_post_act_window'
        act_wnd = self.env.ref(action_xid)
    
        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))
        context.update({'default_discussion_id': self.id})
    
        domain = [('discussion_id', '=', self.id)]
    
        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': act_wnd.res_model,
            'target': 'current',
            'name': _('Posts'),
            'view_mode': act_wnd.view_mode,
            'domain': domain,
            'context': context,
            'search_view_id': act_wnd.search_view_id.id,
            'help': act_wnd.help
        }
    
        return serialized

    # -------------------------------------------------------------------------
    # MOODEL CRUD METHODS
    # -------------------------------------------------------------------------

    def moodle_read(self):
        for record in self:
            record._moodle_read()

    def _moodle_read(self):
        """Retrieve this Moodle discussion by its ID and forum ID"""
        self.ensure_one()

        discussion = self._find_moodle_discussion_record()
        if not discussion:
            err = _('Unable to locate discussion with Moodle ID %s.')
            raise UserError(err % self.moodleid)

        self.content = discussion.get('message', _('Content is empty.'))
        self.name = discussion.get('subject', _('Untitled'))
        self.groupid = discussion.get('groupid', 0)

        message = _('Updated content from discussion with Moodle ID %s.')
        self.message_post(
            body= message % self.moodleid,
            subtype='mail.mt_note'
        )

    def moodle_create(self):
        for record in self:
            record._moodle_create()

    def _moodle_create(self):
        """Create a new discussion in Moodle and return its Moodle ID"""
        self.ensure_one()

        params = {
            'forumid': self.forumid,
            'subject': self.name,
            'message': self.content,
            'groupid': self.groupid or 0,
            # Not valid: 'messageformat': int(self.content_format),
        }
        
        if self.groupid:
            params['groupid'] = self.groupid

        opt_idx = 0
        if self.discussionsubscribe:
            value = int(self.discussionsubscribe)
            params[f'options[{opt_idx}][name]'] = 'discussionsubscribe'
            params[f'options[{opt_idx}][value]'] = value
            opt_idx += 1

        moodle_driver = self.platform_id._get_driver()
        function = 'mod_forum_add_discussion'
        result = moodle_driver.call(function, params)

        discussionid = result.get('discussionid', False)

        if discussionid:
            self.discussionid = discussionid

            pattern = _('Discussion created in Moodle with discussionid %s.')
            self.message_post(body=(pattern % discussionid))

            self._update_moodleid(discussionid)
        else:
            err = _('Failed to retrieve discussionid after Moodle creation.'
                    'Received: %s')
            self.message_post(body=err % str(result))

        return result

    def moodle_write(self):
        raise NotImplementedError(
            'Moodle does not expose a method to update discussions.'
        )

    def _moodle_write(self):
        raise NotImplementedError(
            'Moodle does not expose a method to update discussions.'
        )

    def moodle_unlink(self):
        raise NotImplementedError(
            'Moodle does not expose a method to delete discussions.'
        )

    def _moodle_unlink(self):
        raise NotImplementedError(
            'Moodle does not expose a method to delete discussions.'
        )

    def _update_moodleid(self, discussionid):
        """Search Moodle to get the full discussion post ID"""
        self.ensure_one()

        driver = self.platform_id._get_driver()
        function = 'mod_forum_get_forum_discussions_paginated'
        params = {'forumid': self.forumid}
        response = driver.call(function, params)

        for discussion in response.get('discussions', []):
            if discussion.get('discussion') == discussionid:
                moodleid = discussion.get('id')
                self.moodleid = moodleid

                pattern = _('moodleid for discussion %s set to %s.')
                self.message_post(body=(pattern % (discussionid, moodleid)))

                return

        err = _('Unable to locate moodleid for discussion %s in Moodle.')
        self.message_post(body=err % discussionid)

    def _find_moodle_discussion_record(self, discussionid=None):
        """Finds a Moodle discussion by discussion ID or moodleid"""
        self.ensure_one()

        driver = self.platform_id._get_driver()
        function = 'mod_forum_get_forum_discussions_paginated'
        page = 0
        perpage = 20  # Use maximum allowed if known

        target_id = discussionid or self.moodleid
        field_name = 'discussion' if discussionid else 'id'

        while True:
            params = {
                'forumid': self.forumid,
                'page': page,
                'perpage': perpage
            }
            response = driver.call(function, params)
            discussions = response.get('discussions', [])

            if not discussions:
                break

            for discussion in discussions:
                if discussion.get(field_name) == target_id:
                    return discussion

            page += 1

        return None

    def _update_moodleid(self, discussionid):
        """Update moodleid from discussionid by searching through the forum"""
        discussion = self._find_moodle_discussion_record(
            discussionid=discussionid
        )

        if not discussion:
            err = _('Unable to locate Moodle ID for discussion ID %s.')
            raise UserError(err % discussionid)

        self.moodleid = discussion.get('id')
        message = _('Updated Moodle ID to %s for discussion ID %s.')
        self.message_post(
            body= message % (f'<code>{self.moodleid}</code>', discussionid),
            subtype='mail.mt_note'
        )
