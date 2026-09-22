###############################################################################
#
#    Odoo, Open Source Management Solution
#
#    Copyright (c) All rights reserved:
#        (c) Jorge Soto Garcia, 2025
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses
#
###############################################################################
{  # noqa: B018
    "name": "Facility Management",
    "summary": "Facility and reservation management",
    "description": """
Manage complexes, facilities and shared resources, and schedule reservations
with conflict-free booking.

Key features:

- Facility catalog: complexes, facilities, types, equipment and capacities.
- Reservation management with conflict and availability controls.
- Reservation scheduling for recurring and individual allocations.
- Availability searches and reservation reporting.
- Configurable scheduling and reservation parameters.
- Ownership and access control.
- Email notifications for reservation management.
    """,
    "author": "Jorge Soto Garcia",
    "website": "https://github.com/sotogarcia/odoo-tools",
    "category": "Tools",
    "version": "18.0.1.0.0",
    "depends": [
        "base",
        "mail",
        "record_ownership",
        "base_field_m2m_view",
    ],
    "data": [
        "data/res_groups_data.xml",
        "data/ir_config_parameter_data.xml",
        "data/facility_weekday_data.xml",
        "data/ir_actions_server_data.xml",
        "data/ir_cron_data.xml",
        "data/mail_message_subtype_data.xml",
        "data/mail_notification_email_data.xml",
        "data/mail_templates/mail_layout.xml",
        "data/mail_templates/reservation_requests.xml",
        "data/mail_template_data.xml",
        "views/facility_management.xml",
        "security/facility_management.xml",
        "security/facility_complex.xml",
        "security/facility_facility.xml",
        "security/facility_type.xml",
        "security/facility_reservation.xml",
        "security/facility_weekday.xml",
        "security/facility_reservation_scheduler.xml",
        "security/facility_search_available_wizard.xml",
        "security/facility_reporting_wizard.xml",
        "views/facility_weekday_view.xml",
        "views/facility_complex_view.xml",
        "views/facility_facility_view.xml",
        "views/facility_type_view.xml",
        "views/facility_reservation_view.xml",
        "views/facility_reservation_scheduler_view.xml",
        "views/res_config_settings_view.xml",
        "wizard/facility_search_available_wizard_view.xml",
        "wizard/facility_reporting_wizard_view.xml",
        "report/facility_reservations_report.xml",
    ],
    "demo": [
        "demo/facility_complex_demo.xml",
        "demo/facility_type_demo.xml",
        "demo/facility_facility_demo.xml",
        "demo/facility_reservation_demo.xml",
        "demo/facility_reservation_scheduler_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "facility_management/static/src/js/facility_cog_menu.esm.js",
            "facility_management/static/src/xml/facility_cog_menu.xml",
        ],
        "web.report_assets_common": [
            "facility_management/static/src/css/facility_management_report.css"
        ],
        "web.report_assets_pdf": [
            "facility_management/static/src/css/facility_management_report.css"
        ],
    },
    "external_dependencies": {"python": ["num2words"]},
    "license": "AGPL-3",
}
