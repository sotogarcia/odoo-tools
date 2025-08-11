# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class MoodleApiClientDiscussionPost(models.Model):

    _name = 'moodle.api.client.discussion.post'
    _description = u'Moodle api client discussion post'

    _rec_name = 'name'
    _order = 'write_date DESC, name ASC'

    _inherit = ['moodle.api.client.base']

    discussion_id = fields.Many2one(
        string='Discussion',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help='Related Moodle discussion',
        comodel_name='moodle.api.client.discussion',
        ondelete='cascade'
    )

    parent_id = fields.Many2one(
        string='Parent Post',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Parent post if this is a reply',
        comodel_name='moodle.api.client.discussion.post',
        ondelete='cascade'
    )


    moodle_discussion_id = fields.Integer(
        string='Moodle Discussion ID',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='ID of the Moodle discussion to which this post belongs'
    )

    moodle_parent_post_id = fields.Integer(
        string='Moodle Parent Post ID',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Optional parent post ID in Moodle if this is a reply'
    )

    content = fields.Text(
        string='Content',
        required=True,
        readonly=False,
        index=False,
        default=None,
        help='Initial post content of the discussion thread',
        translate=False
    )

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

    content_format = fields.Selection(
        string='Message Format',
        required=True,
        readonly=False,
        index=False,
        default='1',
        help='Format of the content content',
        selection=[
            ('0', 'Plain Text'),
            ('1', 'HTML'),
        ]
    )

    user_id = fields.Many2one(
        string='Author',
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self._default_user_id(),
        help='User who created the post',
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

    @api.model
    def create(self, values):
        """ Overridden method 'create'
        """

        self._ensure_related_moodleid(
            values, 'discussion_id', 'moodle_discussion_id')
        self._ensure_related_moodleid(
            values, 'parent_id', 'moodle_parent_post_id')

        parent = super(MoodleApiClientDiscussionPost, self)
        result = parent.create(values)
    
        return result
    
    def write(self, values):
        """ Overridden method 'write'
        """
        self._ensure_related_moodleid(
            values, 'discussion_id', 'moodle_discussion_id')
        self._ensure_related_moodleid(
            values, 'parent_id', 'moodle_parent_post_id')
    
        parent = super(MoodleApiClientDiscussionPost, self)
        result = parent.write(values)
    
        return result
    
    def _ensure_related_moodleid(self, values, related_field, moodle_field):
        """If a Many2one field is provided, ensure the corresponding 
           Moodle ID is set.
        """

        item_id = values.get(related_field)
        if not item_id:
            return

        comodel_name = self._fields[related_field].comodel_name
        record = self.env[comodel_name].browse(item_id)

        if record.exists():
            values[moodle_field] = record.moodleid
        else:
            _logger.warning(
                "Cannot find record for field '%s' (ID=%s), skipping "
                "Moodle ID copy.", related_field, item_id
            )
    # -------------------------------------------------------------------------
    # MOODEL CRUD METHODS
    # -------------------------------------------------------------------------

    def moodle_read(self):
        for record in self:
            record._moodle_read()

    def _moodle_read(self):
        """Retrieve this Moodle post by its ID and discussion ID"""
        self.ensure_one()

        result = self.platform_id._get_driver().call(
            'mod_forum_get_discussion_posts',
            {'discussionid': self.moodle_discussion_id}
        )

        for post in result.get('posts', []):
            if post.get('id') == self.moodleid:
                return post

        raise ValueError(
            'Post ID %s not found in discussion %s.' % (
                self.moodleid,
                self.moodle_discussion_id
            )
        )

    def moodle_create(self):
        for record in self:
            record._moodle_create()

    def _moodle_create(self):
        """Create a new post in Moodle and return its Moodle ID"""
        self.ensure_one()

        params = {
            'discussionid': self.moodle_discussion_id,
            'content': self.content,
            'contentformat': int(self.content_format),
            'userid': self.user_id.moodle_user_id,
        }

        if self.moodle_parent_post_id:
            params['parentid'] = self.moodle_parent_post_id

        result = self.platform_id._get_driver().call(
            'mod_forum_add_discussion_post',
            params
        )

        return result

    def moodle_write(self):
        raise NotImplementedError(
            'Moodle does not expose a method to update posts.'
        )

    def _moodle_write(self):
        raise NotImplementedError(
            'Moodle does not expose a method to update posts.'
        )

    def moodle_unlink(self):
        raise NotImplementedError(
            'Moodle does not expose a method to delete posts.'
        )

    def _moodle_unlink(self):
        raise NotImplementedError(
            'Moodle does not expose a method to delete posts.'
        )
