# -*- coding: utf-8 -*-
{
    'name': "Record ownership",

    'summary': 'Allows to indicate the owner of a record',

    'author': "Jorge Soto Garcia",
    'website': "https://github.com/sotogarcia",

    'license': 'LGPL-3',
    'category': 'Technical Settings',
    "version": "18.0.1.0.0",

    'depends': [
        'base'
    ],

    'data': [
        'data/res_groups_data.xml',

        'security/record_ownership_wizard.xml',

        'wizard/record_ownership_wizard_view.xml'
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
