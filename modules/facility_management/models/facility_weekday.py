###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

from ..utils.helpers import check_unique_translation, get_available_copy_value


class FacilityWeekday(models.Model):
    """Weekday catalog used by schedulers (1=Monday ... 7=Sunday)"""

    _name = "facility.weekday"
    _description = "Facility weekday"

    _rec_name = "name"
    _order = "sequence ASC"

    name = fields.Char(
        string="Name",
        required=True,
        readonly=False,
        index=True,
        default=None,
        help="Weekday name (e.g., Monday)",
        size=50,
        translate=True,
    )

    sequence = fields.Integer(
        string="Weekday",
        required=True,
        readonly=True,
        index=True,
        default=1,
        help="ISO weekday number: 1=Monday ... 7=Sunday",
    )

    workday = fields.Boolean(
        string="Workday",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="Check if this weekday is considered a working day",
    )

    _sql_constraints = [  # noqa: RUF012
        (
            "weekday_sequence_range",
            "CHECK(sequence BETWEEN 1 AND 7)",
            "Weekday must be between 1 (Monday) and 7 (Sunday)",
        ),
        (
            "weekday_sequence_unique",
            "UNIQUE(sequence)",
            "There is already a weekday with this sequence",
        ),
    ]

    @api.constrains("name")
    def _check_name(self):
        check_unique_translation(
            self,
            field_name="name",
            message=_("There is already a weekday with this name"),
        )
