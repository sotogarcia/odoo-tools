# -*- coding: utf-8 -*-
{
    'name': 'Facility Management',

    'summary': '''
        Small facility management module to be used in academies''',

    'description': '''
        Small facility management module to be used in academies
    ''',

    'author': 'Jorge Soto Garcia',
    'website': 'https://github.com/sotogarcia',

    'category': 'Tools',
    'version': '13.0.1.0.0',

    'depends': [
        'base',
        'record_ownership',
        'base_field_m2m_view',
        'mail'
    ],

    'data': [
        'data/res_groups_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/facility_weekday_data.xml',
        'data/ir_actions_server_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_notification_email_data.xml',

        'views/facility_management.xml',

        'security/facility_management.xml',
        'security/facility_complex.xml',
        'security/facility_facility.xml',
        'security/facility_type.xml',
        'security/facility_reservation.xml',
        'security/facility_weekday.xml',
        'security/facility_reservation_scheduler.xml',
        'security/facility_complex_reservation_rel.xml',

        'views/facility_weekday_view.xml',
        'views/facility_complex_view.xml',
        'views/facility_facility_view.xml',
        'views/facility_type_view.xml',
        'views/facility_reservation_view.xml',
        'views/facility_reservation_scheduler_view.xml',
        'views/res_config_settings_view.xml',

        'wizard/facility_search_available_wizard_view.xml',
        'wizard/facility_reporting_wizard_view.xml',
        'wizard/facility_reservation_massive_actions_wizard_view.xml',

        'report/facility_report.xml'
    ],

    'demo': [
        'demo/facility_complex_demo.xml',
        'demo/facility_type_demo.xml',
        'demo/facility_facility_demo.xml',
        'demo/facility_reservation_demo.xml',
        'demo/facility_reservation_scheduler_demo.xml'
    ],

    'js': [
        'static/src/js/header_view_buttons.js',
        'static/src/js/facility_management_widgets.js'
    ],

    'css': [
        'static/src/css/facility_management.css',
        'static/src/css/facility_management_report.css'
    ],

    'qweb': [
        "static/src/xml/header_view_buttons.xml",
        "static/src/xml/facility_management_widgets.xml"
    ],


    "external_dependencies": {
        "python": [
            'num2words'
        ]
    },

    'license': 'AGPL-3'
}
