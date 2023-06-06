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
    'name': 'Calendar filter toggle buttons',
    'summary': 'Calendar filter toggle buttons',
    'version': '1.0',

    'description': 'Calendar filter toggle buttons',

    'author': 'Jorge Soto Garcia',
    'maintainer': 'Jorge Soto Garcia',
    'contributors': ['<sotogarcia@gmail.com>'],

    'website': 'http://www.gitlab.com/sotogarcia',

    'license': 'AGPL-3',
    'category': 'Extra Tools',

    'depends': [
        'base'
    ],

    'data': [
        'views/calendar_filter_toggle_button.xml'
    ],

    'js': [
        'static/src/js/web_calendar.js'
    ],

    'qweb': [
        'static/src/xml/web_calendar.xml',
    ],

    'installable': True
}
