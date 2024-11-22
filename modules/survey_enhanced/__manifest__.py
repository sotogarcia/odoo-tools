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
    'name': 'Survey enhanced',
    'version': '1.0',

    'summary': '''Extended functionality for Odoo Surveys, enabling advanced
    survey configurations, automation, and custom reporting.''',

    'description': '''
    Survey Enhanced extends Odoo's Survey module with additional functionality
    for managing and automating surveys. This module includes:
    - Advanced survey scheduling with options for repeat intervals, expiration,
    and automated invites.
    - Enhanced data export options, allowing CSV export with customized
    delimiter, encoding, and date formatting.
    - Integration with facilities and training records for targeted feedback
    surveys.
    - Configurable email templates for automated survey invites.

    Ideal for organizations looking to leverage Odoo's survey tool for enhanced
    feedback management and analytics.
    ''',

    'author': 'Jorge Soto Garcia',
    'maintainer': 'Jorge Soto Garcia',
    'contributors': ['Jorge Soto Garcia <sotogarcia@gmail.com>'],

    'website': 'http://www.gitlab.com/sotogarcia',

    'license': 'AGPL-3',
    'category': 'Marketing/Survey',

    'depends': [
        'base',
        'survey',
        'website',
        'record_ownership'
    ],
    'external_dependencies': {
        'python': [
        ],
    },
    'data': [
        'views/survey_survey_view.xml',
        'views/survey_question_view.xml',
        'views/survey_templates.xml'
    ],
    'demo': [
    ],
    'js': [
    ],
    'css': [
    ],
    'qweb': [
    ],
    'images': [
    ],
    'test': [
    ],

    'installable': True
}
