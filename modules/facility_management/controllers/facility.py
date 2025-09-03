# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo.http import Controller, route
from odoo.http import request

from logging import getLogger


_logger = getLogger(__name__)


REPORT = ('report.facility_management.'
          'view_facility_qweb')


class Facility(Controller):
    """ Allow to publish facility timetables
    """

    @route('/facility/timetable', type='http', auth='none', website="True")
    def facility_timetable(self, **kw):
        facility_obj = request.env['facility.facility'].sudo()
        facility_set = facility_obj.search([])

        report_obj = request.env[REPORT].sudo()

        values = report_obj._get_report_values(facility_set.mapped('id'))

        return request.render('facility_management.view_facility_qweb', values)
