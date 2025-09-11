# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _

from logging import getLogger


_logger = getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """Module configuration attributes"""

    _inherit = ["res.config.settings"]

    auto_archive_on_rejection = fields.Boolean(
        string="Auto archive",
        required=False,
        readonly=False,
        index=False,
        default=False,
        help=(
            "If enabled, records will be automatically archived when they "
            "are rejected"
        ),
        config_parameter="facility_management.auto_archive_on_rejection",
    )

    week_start_day = fields.Many2one(
        string="Week start day",
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self.env.ref(
            "facility_management.facility_weekday_monday"
        ),
        help="Day considered as the start of the week.",
        comodel_name="facility.weekday",
        domain=[],
        context={},
        ondelete="restrict",
        auto_join=False,
        config_parameter="facility_management.week_start_day",
    )

    availability_margin_minutes = fields.Integer(
        string="Availability margin (minutes)",
        required=True,
        readonly=False,
        index=False,
        default=60,
        help="Number of minutes after now during which future reservations "
        "will mark a facility as unavailable.",
        config_parameter="facility_management.availability_margin_minutes",
    )
