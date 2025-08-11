# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class MoodleApiClientPage(models.Model):

    _name = 'moodle.api.client.page'
    _description = u'Moodle api client page'

    _rec_name = 'name'
    _order = 'write_date DESC, name ASC'

    _inherit = ['moodle.api.client.base']

    course_id = fields.Integer(
        string='Course ID',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help=('Moodle course ID required to create the page, not required '
              'for syncing an existing one')
    )

    section_id = fields.Integer(
        string='Section ID',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help=('Moodle section ID required to create the page, not required '
              'for syncing an existing one')
    )

    content = fields.Text(
        string='Content',
        required=True,
        readonly=False,
        index=False,
        default=None,
        help='HTML content of the Moodle page',
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
        string='Content Format',
        required=True,
        readonly=False,
        index=False,
        default='1',
        help='Format of the page content',
        selection=[
            ('0', 'Plain Text'),
            ('1', 'HTML'),
        ]
    )

    # - Field: selection_method_id (default)
    # ------------------------------------------------------------------------

    user_id = fields.Many2one(
        string='Author',
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self._default_user_id(),
        help='User who created the page',
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

    moodle_user_id = fields.Integer(
        string='Moodle User ID',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='ID of the corresponding user in Moodle',
        related="user_id.moodle_user_id"
    )

    # -------------------------------------------------------------------------
    # MOODEL CRUD METHODS
    # -------------------------------------------------------------------------
    
    def moodle_read(self):
        for record in self:
            record._moodle_read()

    def _moodle_read(self):
        """Retrieve this Moodle page by its ID and course ID"""
        self.ensure_one()

        result = self.platform_id._get_driver().call(
            'mod_page_get_pages_by_courses',
            {'courseids[0]': self.course_id}
        )

        for page in result.get('pages', []):
            if page.get('id') == self.moodleid:
                return page

        raise ValueError(
            'Page ID %s not found in course %s.' % (
                self.moodleid,
                self.course_id
            )
        )

    def moodle_create(self):
        for record in self:
            record._moodle_create()

    def _moodle_create(self):
        """Create a new page in Moodle and return its Moodle ID"""
        self.ensure_one()

        params = {
            'courseid': self.course_id,
            'name': self.name,
            'intro': self.content,
            'introformat': int(self.content_format),
            'section': self.section_id,
            'visible': 1
        }

        result = self.platform_id._get_driver().call(
            'core_notes_create_notes',
            params
        )

        print(result)

        return result

    def moodle_write(self):
        for record in self:
            record._moodle_write()

    def _moodle_write(self):
        """Update the page in Moodle"""
        self.ensure_one()

        params = {
            'id': self.moodleid,
            'name': self.name,
            'intro': self.content,
            'introformat': int(self.content_format)
        }

        return self.platform_id._get_driver().call(
            'mod_page_update_instance',
            params
        )

    def moodle_unlink(self):
        for record in self:
            record._moodle_unlink()

    def _moodle_unlink(self):
        """Delete this Moodle page (by Course Module ID)"""
        self.ensure_one()

        return self.platform_id._get_driver().call(
            'core_course_delete_module',
            {'cmid': self.moodleid}
        )
