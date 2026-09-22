###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo.http import Controller, request, route


_REPORT = "report.facility_management.report_facility_reservations"
_TEMPLATE = "facility_management.report_facility_reservations"


class Facility(Controller):
    """Allow to publish facility timetables."""

    @route(
        "/facility/timetable",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def facility_timetable(self, **kw):
        facility_set = request.env["facility.facility"].search([])

        report = request.env[_REPORT]
        values = report._get_report_values(facility_set.ids)

        return request.render(_TEMPLATE, values)
