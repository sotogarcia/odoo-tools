# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class FacilityWeekDay(models.Model):
    """ Weekday numbers
    """

    _name = 'facility.weekday'
    _description = u'Facility weekdays'

    _rec_name = 'name'
    _order = 'sequence ASC'

    name = fields.Char(
        string='Name',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Name of the day of the week',
        size=50,
        translate=True
    )

    workday = fields.Boolean(
        string='Workday',
        required=False,
        readonly=False,
        index=True,
        default=False,
        help='If checked then this is a business day'
    )

    sequence = fields.Integer(
        string='Sequence',
        required=True,
        readonly=False,
        index=True,
        default=0,
        help='Position occupied by the day in the week'
    )
