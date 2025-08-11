# -*- coding: utf-8 -*-
###############################################################################
#    Moodle 3.4.3 driver for Moodle API Client                                #
###############################################################################

import requests
from .base_driver import BaseMoodleDriver


class MoodleDriver_03_04_03(BaseMoodleDriver):
    """Driver implementation for Moodle 3.4.3+"""

    def call(self, function, parameters):
        """Perform a generic API call to the Moodle REST service"""
        payload = {
            'wstoken': self.token,
            'moodlewsrestformat': 'json',
            'wsfunction': function,
        }
        payload.update(parameters)

        response = requests.post(
            url=f"{self.url}/webservice/rest/server.php",
            data=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_authenticated_user(self):
        """Return full info of the user linked to the token."""
        return self.call('core_webservice_get_site_info', {})

    def get_authenticated_user_id(self):
        """Return the Moodle user ID linked to the current token."""
        result = self.get_authenticated_user()

        user_id = result.get('userid')

        if user_id is None:
            raise ValueError(
                'Authenticated user ID not found in Moodle response.'
            )

        return int(user_id)

    def get_user(self, user_id):
        """Retrieve user information from Moodle by user ID"""
        return self.call('core_user_get_users_by_field', {
            'field': 'id',
            'values[0]': user_id
        })

    def get_courses(self):
        """Retrieve all visible courses from Moodle"""
        return self.call('core_course_get_courses', {})
