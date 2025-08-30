# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields
from odoo.tools.translate import _
from logging import getLogger


_logger = getLogger(__name__)


class FacilityWeekday(models.Model):
    """ Weekday catalog used by schedulers (1=Monday ... 7=Sunday)
    """

    _name = 'facility.weekday'
    _description = 'Facility weekday'

    _rec_name = 'name'
    _order = 'sequence ASC'

    name = fields.Char(
        string='Name',
        required=True,
        readonly=False,
        index=True,
        default=None,
        help='Weekday name (e.g., Monday)',
        size=50,
        translate=True
    )

    sequence = fields.Integer(
        string='Weekday',
        required=True,
        readonly=False,
        index=True,
        default=1,
        help='ISO weekday number: 1=Monday ... 7=Sunday'
    )

    workday = fields.Boolean(
        string='Workday',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='Check if this weekday is considered a working day'
    )

    active = fields.Boolean(
        string='Active',
        required=False,
        readonly=False,
        index=False,
        default=True,
        help='Enables/disables the record'
    )

    _sql_constraints = [
        (
            'weekday_sequence_range',
            'CHECK(sequence BETWEEN 1 AND 7)',
            _('Weekday must be between 1 (Monday) and 7 (Sunday)')
        ),
        (
            'weekday_sequence_unique',
            'UNIQUE(sequence)',
            _('There is already a weekday with this sequence')
        ),
        (
            'weekday_name_unique',
            'UNIQUE(name)',
            _('There is already a weekday with this name')
        ),
    ]
