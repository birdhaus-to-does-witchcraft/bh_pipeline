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
from wix_api.orders import OrdersAPI
from wix_api.tickets import TicketsAPI
from wix_api.ticket_definitions import TicketDefinitionsAPI
from wix_api.transactions import TransactionsAPI
from wix_api.payments import PaymentsAPI
from wix_api.members import MembersAPI
from wix_api.forms import FormsAPI
from wix_api.coupons import CouponsAPI
from wix_api.automations import AutomationsAPI

__all__ = [
    "WixAPIClient",
    "EventsAPI",
    "GuestsAPI",
    "RSVPAPI",
    "ContactsAPI",
    "OrdersAPI",
    "TicketsAPI",
    "TicketDefinitionsAPI",
    "TransactionsAPI",
    "PaymentsAPI",
    "MembersAPI",
    "FormsAPI",
    "CouponsAPI",
    "AutomationsAPI",
]
