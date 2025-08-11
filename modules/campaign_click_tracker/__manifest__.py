# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#
#    Copyright (c) All rights reserved:
#        (c) 2025 Jorge Soto Garcia
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
    'name': 'Campaign Click Tracker',
    'summary': 'Track partner responses to campaign links via unique tokens',
    'version': '13.0.1.0.0',

    'description': '''
Campaign Click Tracker
======================

This module allows the creation of marketing campaigns and tracking of partner responses via email links. Each link includes a unique token and a response code. When clicked, the link registers the partner's response automatically.

Features:
- Campaign and partner linking
- Unique token generation per link
- Response logging through GET parameters
- Public endpoint for tracking clicks
''',

    'author': 'Jorge Soto Garcia',
    'maintainer': 'Jorge Soto Garcia',
    'contributors': [
        'Jorge Soto Garcia <sotogarcia@gmail.com>'
    ],

    'website': 'http://www.gitlab.com/sotogarcia',

    'license': 'AGPL-3',
    'category': 'Marketing',

    'depends': [
        'base',
        'mail',
        'mass_mailing'
    ],
    'external_dependencies': {
        'python': [],
    },
    'data': [
        'security/campaign_click_tracker_answer.xml',
        'security/campaign_click_tracker_campaign.xml',
        'security/campaign_click_tracker_user_input.xml',
        'views/campaign_click_tracker.xml',
        'views/campaign_templates.xml',
        'views/campaign_click_tracker_answer_view.xml',
        'views/campaign_click_tracker_campaign_view.xml',
        'views/campaign_click_tracker_user_input_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'images': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}

