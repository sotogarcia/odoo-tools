# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields
from logging import getLogger
from odoo.tools.translate import _


_logger = getLogger(__name__)


class FacilityType(models.Model):
    """Type of facility"""

    _name = "facility.type"
    _description = "Facility type"

    _rec_name = "name"
    _order = "name ASC"

    name = fields.Char(
        string="Name",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Name of the facility type",
        size=255,
        translate=True,
    )

    description = fields.Text(
        string="Description",
        required=False,
        readonly=False,
        index=False,
        default=None,
        help="Additional details or notes about this facility type",
        translate=True,
    )

    active = fields.Boolean(
        string="Active",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="Enables/disables the record",
    )

    is_space = fields.Boolean(
        string="Is space",
        required=False,
        readonly=False,
        index=True,
        default=False,
        help="Check this option if the record represents a physical space.",
    )

    _sql_constraints = [
        (
            "unique_facility_type_name",
            'UNIQUE("name")',
            "Facility type already exists",
        )
    ]
