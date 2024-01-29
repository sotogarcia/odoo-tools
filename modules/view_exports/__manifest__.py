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
    'name': 'View exports',
    'summary': 'Allow to view and export ir.exports records',
    'version': '1.0',

    'description': 'Allow to view and export ir.exports records',

    'author': 'Jorge Soto García',
    'maintainer': 'Jorge Soto García',
    'contributors': ['Jorge Soto García <sotogarcia@gmail.com>'],

    'website': 'http://www.gitlab.com/sotogarcia',

    'license': 'LGPL-3',
    'category': 'Technical Settings',
    'version': '13.0.1.3',

    'depends': [
        'base'
    ],
    'external_dependencies': {
        'python': [
        ],
    },
    'data': [
        'data/ir_exports_data.xml',

        'views/ir_exports_view.xml',
        'views/ir_exports_line_view.xml'
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
