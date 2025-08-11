# -*- coding: utf-8 -*-
###############################################################################
#    Base driver class for Moodle API clients.                                #
#    Each specific Moodle version driver should inherit from this class.     #
###############################################################################

from abc import ABCMeta, abstractmethod
from time import mktime
from datetime import datetime


class BaseMoodleDriver(object):
    """Abstract base class for Moodle API drivers"""

    __metaclass__ = ABCMeta

    def __init__(self, url, token):
        if type(self) is BaseMoodleDriver:
            raise NotImplementedError(
                'BaseMoodleDriver is abstract and cannot be instantiated directly.'
            )
        self.url = url
        self.token = token

    @abstractmethod
    def call(self, function, parameters):
        """Perform the actual API call to Moodle"""
        raise NotImplementedError('Method call() must be implemented by the subclass.')
            
    @abstractmethod
    def get_authenticated_user(self):
        """Return info about the user linked to the current token."""
        raise NotImplementedError(
            'Method get_authenticated_user() must be implemented.'
        )

    @abstractmethod
    def get_authenticated_user_id(self):
        """Return the Moodle user ID linked to the token."""
        raise NotImplementedError(
            'Method get_authenticated_user_id() must be implemented.'
        )

    @abstractmethod
    def get_user(self, user_id):
        """Retrieve user data from Moodle"""
        raise NotImplementedError('Method get_user() must be implemented by the subclass.')

    @abstractmethod
    def get_courses(self):
        """Retrieve list of courses from Moodle"""
        raise NotImplementedError('Method get_courses() must be implemented by the subclass.')

    # Optional: allow JSON conversion of model objects
    def prepare_payload(self, record):
        """Optional helper to convert a record to Moodle-compatible payload"""
        if hasattr(record, 'to_moodle_json'):
            return record.to_moodle_json()
        raise ValueError("Record does not implement 'to_moodle_json()'")

    @staticmethod
    def datetime_to_timestamp(dt):
        if dt:
            return int(time.mktime(dt.timetuple()))
        
        return 0  # Moodle admite 0 como "sin fecha"

    @staticmethod
    def timestamp_to_datetime(ts):
        if ts:
            return datetime.fromtimestamp(ts)
        
        return False

