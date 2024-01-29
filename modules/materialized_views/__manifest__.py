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
    'name': 'Materialized Views',
    'summary': 'Models based on PostgreSQL materialized views',
    'version': '13.0.1.3',

    'description': """
This Odoo module streamlines the process of integrating PostgreSQL materialized
views into the Odoo framework, enabling developers to efficiently create and
manage models based on these views. Materialized views offer a powerful way to
optimize complex queries by storing query results as a physical table which can
be refreshed periodically. This approach significantly improves performance for
read-heavy operations, making it ideal for reporting and analytics.
    """,

    'author': 'Jorge Soto Garcia',
    'maintainer': 'Jorge Soto Garcia',
    'contributors': ['Jorge Soto Garcia <sotogarica@gmail.com>'],

    'website': 'http://www.gitlab.com/sotogarcia',

    'license': 'AGPL-3',
    'category': 'Technical Settings',

    'depends': [
        'base'
    ],
    'external_dependencies': {
        'python': [
        ],
    },
    'data': [
        'data/ir_cron_data.xml'
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
