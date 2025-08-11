# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from .moodle_03_04_03 import MoodleDriver_03_04_03

def get_driver(version, url, token):
    if version == '3.4.3':
        from .moodle_03_04_03 import MoodleDriver_03_04_03
        return MoodleDriver_03_04_03(url, token)

    message = f"No driver implemented for Moodle version {version}"
    raise NotImplementedError(message)
