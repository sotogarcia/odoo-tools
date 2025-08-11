# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#
#    Copyright (c) All rights reserved:
#        (c) 2015  
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses
#
###############################################################################
{
    'name': 'Moodle API Client',
    'summary': 'Moodle API Client Module Project',
    'version': '1.0',
    'description': """
Moodle API Client Module Project.
=================================

This module provides an integration with Moodle 3.4.3+ through its external API.
It allows for synchronization and communication between Odoo 13 and a Moodle
instance, making it possible to fetch and manage course data, users, enrolments,
grades, and other resources.

Note: This version is designed with future Moodle versions in mind.
    """,
    'author': 'Jorge Soto Garcia',
    'maintainer': 'Jorge Soto Garcia',
    'contributors': ['Jorge Soto Garcia <sotogarcia@gmail.com>'],
    'website': 'http://www.gitlab.com/sotogarcia',
    'license': 'AGPL-3',
    'category': 'Education',
    'depends': [
        'base',
        'mail'
    ],
    'external_dependencies': {
        'python': [
            'requests',
        ],
    },
    'data': [
        'data/ir_action_server_data.xml',
        
        'security/moodle_api_client_platform.xml',
        'security/moodle_api_client_course.xml',
        'security/moodle_api_client_forum.xml',
        'security/moodle_api_client_discussion.xml',
        'security/moodle_api_client_discussion_post.xml',
        'security/moodle_api_client_calendar_event.xml',

        'views/moodle_api_client_view.xml',
        'views/moodle_api_client_platform_view.xml', 
        'views/moodle_api_client_course_view.xml',
        'views/moodle_api_client_forum_view.xml',
        'views/moodle_api_client_discussion_view.xml', 
        'views/moodle_api_client_discussion_post_view.xml', 
        'views/moodle_api_client_calendar_event_view.xml',

        'wizard/moodle_api_client_res_users_wizard_view.xml'
    ],
    'demo': [
        # Demo data (if any)
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}




