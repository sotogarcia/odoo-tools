# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields
from odoo.tools import drop_view_if_exists

from logging import getLogger


_logger = getLogger(__name__)


class FacilityComplexFacilityReservationRel(models.Model):
    """This act as middle relation in many to many relationship between
    model.name and model.name
    """

    _name = "facility.complex.facility.reservation.rel"
    _description = "Facility complex facility reservation"

    _order = "create_date DESC"

    _auto = False

    _check_company_auto = True

    complex_id = fields.Many2one(
        string="Complex",
        required=True,
        readonly=True,
        index=True,
        default=None,
        help="A group of facilities, usually in the same location",
        comodel_name="facility.complex",
        domain=[],
        context={},
        ondelete="cascade",
        auto_join=False,
    )

    company_id = fields.Many2one(
        string="Company", related="complex_id.company_id", store=True
    )

    reservation_id = fields.Many2one(
        string="Reservation",
        required=True,
        readonly=True,
        index=True,
        default=None,
        help="Selected time slot indicating when the facility is reserved",
        comodel_name="facility.reservation",
        domain=[],
        context={},
        ondelete="cascade",
        auto_join=False,
    )

    state = fields.Selection(
        string="State",
        required=True,
        readonly=False,
        index=True,
        default="requested",
        help="Current reservation status",
        selection=[
            ("requested", "Requested"),
            ("confirmed", "Confirmed"),
            ("rejected", "Rejected"),
        ],
        groups="facility_management.facility_group_monitor",
    )

    def prevent_actions(self):
        actions = ["INSERT", "UPDATE", "DELETE"]

        BASE_SQL = """
            CREATE OR REPLACE RULE {table}_{action} AS
                ON {action} TO {table} DO INSTEAD NOTHING
        """

        for action in actions:
            sql = BASE_SQL.format(table=self._table, action=action)
            self.env.cr.execute(sql)

    def init(self):
        sentence = """CREATE or REPLACE VIEW {} as ({})"""

        drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute(sentence.format(self._table, self._view_sql))

        self.prevent_actions()

    # Raw sentence used to create new model based on SQL VIEW
    _view_sql = """
        SELECT DISTINCT ON (fr."id")
            fr."id" AS id,
            fc."id" AS complex_id,
            fr."id" AS reservation_id,
            fr.create_date,
            fr.create_uid,
            fr.write_date,
            fr.write_uid,
            fr."state"
        FROM
            facility_complex AS fc
        INNER JOIN facility_facility AS ff
            ON ff.complex_id = fc."id" AND ff.active
        INNER JOIN facility_reservation AS fr
            ON fr.facility_id = ff."id"
    """
