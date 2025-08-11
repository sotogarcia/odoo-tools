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
    'name': 'Attachment Effective URL',
    'summary': 'Adds a computed URL for accessing attachments, whether file or link',
    'version': '13.0.1.0.0',

    'description': """
Attachment Effective URL

This module adds a computed field `effective_url` to `ir.attachment`, returning:
- The original URL if the attachment is of type 'url'.
- A generated download URL if the attachment is a binary file.

Useful for unified link handling in portals, reports, and automation.
    """,

    'author': 'Jorge Soto Garcia',
    'maintainer': 'Jorge Soto Garcia',
    'contributors': ['Jorge Soto Garcia <JorgeSotoGarcia@gmail.com>'],

    'website': 'http://www.gitlab.com/sotogarcia',

    'license': 'AGPL-3',
    'category': 'Tools',

    'depends': [
        'base'
    ],

    'external_dependencies': {
        'python': [],
    },

    'installable': True,
}
