###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _


class ResConfigSettings(models.TransientModel):
    """Module configuration attributes"""

    _inherit = ["res.config.settings"]  # noqa: RUF012

    auto_archive_on_rejection = fields.Boolean(
        string="Auto archive",
        required=False,
        readonly=False,
        index=False,
        default=False,
        help="Automatically archive records upon rejection.",
        config_parameter="facility_management.auto_archive_on_rejection",
    )

    week_start_day = fields.Many2one(
        string="Week start day",
        required=True,
        readonly=False,
        index=False,
        default=lambda self: self._default_first_weekday(),
        help="Day designated as the start of the week.",
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
        help="Minutes after current time marking reservations unavailable.",
        config_parameter="facility_management.availability_margin_minutes",
    )

    @api.model
    def _default_first_weekday(self):
        external_id = "facility_management.facility_weekday_monday"
        return self.env.ref(external_id, raise_if_not_found=False)
