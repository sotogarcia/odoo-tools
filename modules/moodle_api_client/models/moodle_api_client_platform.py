# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools import safe_eval
from odoo.exceptions import UserError

from logging import getLogger


_logger = getLogger(__name__)


class MoodleApiClientPlatform(models.Model):

    _name = 'moodle.api.client.platform'
    _description = 'Moodle API Client Platform'

    _inherit = ['mail.thread']

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Internal name of the Moodle platform'
    )

    description = fields.Text(
        string='Description',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Optional description of this platform instance'
    )

    active = fields.Boolean(
        string='Active',
        required=False,
        readonly=False,
        index=True,
        default=True,
        help='Enable or disable this vacancy position without deleting it',
        track_visibility='onchange'
    )

    url = fields.Char(
        string='Moodle URL',
        required=True,
        readonly=False,
        index=False,
        default=None,
        help='Base URL of the Moodle instance (e.g. https://moodle.example.com)'
    )

    driver_name = fields.Selection(
        string='Moodle Driver',
        required=True,
        readonly=False,
        index=False,
        default='moodle_03_04_03',
        help='Identifier of the Moodle driver to use',
        selection=[
            ('moodle_03_04_03', 'Moodle 3.4.3+'),
        ]
    )

    default_user_id = fields.Many2one(
        string='Default User',
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self._default_user_id(),
        help='Odoo user used for synchronization if no other user is defined',
        comodel_name='res.users',
        ondelete='set null',
        auto_join=False
    )

    def _default_user_id(self):
        try:
            return self.env.user.id or self.env.ref('base.user_root').id
        except Exception:
            return 1  # fallback to superuser ID

    moodle_user_id = fields.Integer(
        string='Moodle User ID',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='ID of the corresponding user in Moodle',
        related="default_user_id.moodle_user_id"
    )

    moodle_api_token = fields.Char(
        string='Moodle API token',
        required=True,
        readonly=True,
        index=False,
        default=None,
        help='Authentication token to access the Moodle API as this user',
        translate=False,
        related="default_user_id.moodle_api_token"
    )

    course_ids = fields.One2many(
        string='Courses',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help=False,
        comodel_name='moodle.api.client.course',
        inverse_name='platform_id',
        domain=[],
        context={},
        auto_join=False,
        limit=None
    )

    # - Field: discussion_count (compute)
    # ------------------------------------------------------------------------

    course_count = fields.Integer(
        string='Course count',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help=False,
        compute='_compute_course_count'
    )

    @api.depends('course_ids')
    def _compute_course_count(self):
        for record in self:
            record.course_count = len(record.course_ids)

    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------

    def _get_driver(self):
        """Return the driver instance based on current record."""
        MoodleClientBase = self.env['moodle.api.client.base']
        DriverClass = MoodleClientBase._get_driver_class(self.driver_name)
        return DriverClass(self.url, self.moodle_api_token)

    # -------------------------------------------------------------------------
    # CHECK_CONNECTION CODE
    # -------------------------------------------------------------------------

    def check_connection(self):
        """Check Moodle connection and match user ID with expected value."""
        for platform in self:
            platform._check_connection()

    def _check_connection(self):
        try:
            driver = self._get_driver()

            # Ask Moodle for token-bound user info
            result = driver.call(
                'core_webservice_get_site_info',
                {}
            )

            actual_id = int(result.get('userid', 0))
            expected_id = self.moodle_user_id

            if actual_id != expected_id:
                message = _(
                    'Moodle responded with user ID %s, '
                    'but expected %s.'
                )
                raise UserError(message % (actual_id, expected_id))

            message = _('Connection successful. User ID %s verified.')
            self.message_post(
                body=message % actual_id,
                subtype='mail.mt_note'
            )

        except Exception as error:
            message = _('Connection check failed: %s')
            raise UserError(message % str(error))

    # -------------------------------------------------------------------------
    # SYNCHRONIZE_COURSES CODE
    # -------------------------------------------------------------------------

    def synchronize_courses(self):
        for record in self:
            record._synchronize_courses()

    def _synchronize_courses(self):
        """Finds a Moodle discussion by discussion ID or moodleid"""
        self.ensure_one()

        course_obj = self.env['moodle.api.client.course']

        driver = self._get_driver()

        function = 'core_course_get_courses'
        response = driver.call(function, {})
        if (
            isinstance(response, dict) 
            and response.get('errorcode') == 'errorcoursecontextnotvalid'
        ):
            function = 'core_enrol_get_users_courses'
            params = {'userid': self.user_id.moodle_user_id}
            response = driver.call(function, params)

        if not isinstance(response, list) and response:
            return None

        for course in response:
            moodleid = course.get('id')

            startdate = course.get('startdate')
            enddate = course.get('enddate')

            values = {
                'name': course.get('fullname'),
                'shortname': course.get('shortname'),
                'summary': course.get('summary'),
                # 'summaryformat': course.get('summaryformat'),
                'visible': bool(course.get('visible') or 1),
                'startdate': driver.timestamp_to_datetime(startdate),
                'enddate': driver.timestamp_to_datetime(enddate)
            }

            course_record = self.course_ids.filtered(
                lambda d: d.moodleid == moodleid
            )
            if course_record:
                course_record = course_record[0]
                course_record.write(values)
            else:
                values['platform_id'] = self.id
                values['moodleid'] = moodleid
                course_obj.create(values)

        return None

    # -------------------------------------------------------------------------
    # OTHER PUBLIC METHODS
    # -------------------------------------------------------------------------
    
    def view_courses(self):
        self.ensure_one()
    
        action_xid = 'moodle_api_client.action_moodle_course_act_window'
        act_wnd = self.env.ref(action_xid)
        
        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))
        context.update({'default_platform_id': self.id})
    
        domain = [('platform_id', '=', self.id)]
    
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
