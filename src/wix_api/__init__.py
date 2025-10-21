"""
Wix API client library.

This package provides Python wrappers for Wix REST APIs with validated endpoints.
All endpoints verified against official Wix developer documentation (October 2025).
"""

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from wix_api.guests import GuestsAPI
from wix_api.rsvp import RSVPAPI
from wix_api.contacts import ContactsAPI
from wix_api.transactions import TransactionsAPI

__all__ = [
    "WixAPIClient",
    "EventsAPI",
    "GuestsAPI",
    "RSVPAPI",
    "ContactsAPI",
    "TransactionsAPI",
]
