# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models

from logging import getLogger

_logger = getLogger(__name__)


class FacilityReport(models.AbstractModel):
    """ Custom report behavior
    """

    _name = ('report.facility_management.'
             'view_facility_qweb')

    _inherit = ['time.span.report.mixin']

    _table = 'facility_report'
    _description = u'Facility reservation report'

    def _read_record_values(self, reservation):
        owner = reservation.owner_id.name
        facility = reservation.facility_id.name

        return {
            'id': reservation.id,
            'date': self.date_str(reservation.date_start),
            'interval': self.time_str(reservation),
            'name': reservation.display_name,
            'description': reservation.description,
            'owner': owner,
            'facility': facility
        }

    def _get_report_values(self, docids, data=None):
        data = data or {}
        docids = docids or data.get('doc_ids', [])

        date_start, date_stop = self._get_interval(data)
        full_weeks = data.get('full_weeks', True)

        lang = self._get_lang()

        facility_obj = self.env['facility.facility']

        domain = [('id', 'in', docids)]
        facility_set = facility_obj.search(domain)

        in_date = self._in
        values = {}

        for facility in facility_set:
            values[facility.id] = {
                'id': facility.id,
                'name': facility.name,
                'weeks': {}
            }

            for current in self._date_range(date_start, date_stop, full_weeks):

                week = self._week_str(current)
                reservations = facility.reservation_ids.filtered(
                    lambda s: in_date(s, current))

                if week not in values[facility.id]['weeks']:
                    values[facility.id]['weeks'].update({week: {}})

                date_name = self.date_str(current)
                if date_name not in values[facility.id]['weeks'][week]:
                    values[facility.id]['weeks'][week].update({date_name: {}})

                for rv in reservations:
                    values[facility.id]['weeks'][week][date_name][rv.id] = \
                        self._read_record_values(rv)

        docargs = {
            'doc_ids': docids,
            'doc_model': facility_obj,
            'data': data,
            'docs': facility_set,
            'report': self,
            'values': values,
            'lang': lang
        }

        return docargs
