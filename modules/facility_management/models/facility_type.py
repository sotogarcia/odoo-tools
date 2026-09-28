###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models
from odoo.tools.translate import _

from ..utils.helpers import check_unique_translation, get_available_copy_value


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

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()

        default = dict(default or {})

        if "name" not in default:
            default["name"] = get_available_copy_value(
                self,
                field_name="name",
                value=self.name,
            )

        return super().copy(default)

    @api.constrains("name")
    def _check_name(self):
        check_unique_translation(
            self,
            field_name="name",
            message=_("There is already a facility type with this name"),
        )
