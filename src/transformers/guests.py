"""
Guests data transformer.

Transforms raw Wix Events Guests API data into clean, analysis-ready format.
Handles RSVP guests, buyers, and ticket holders.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class GuestsTransformer(BaseTransformer):
    """Transform raw Wix guests data into clean, flattened format."""

    @staticmethod
    def transform_guest(guest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single guest from raw API format to flattened format.

        Args:
            guest: Raw guest data from Wix API

        Returns:
            Flattened guest data suitable for CSV export
        """
        transformed = {}

        # Basic fields
        transformed['guest_id'] = guest.get('id')
        transformed['event_id'] = guest.get('eventId')
        transformed['contact_id'] = guest.get('contactId')
        transformed['guest_type'] = guest.get('guestType')  # RSVP, BUYER, TICKET_HOLDER

        # RSVP information (only for RSVP guests)
        transformed['rsvp_id'] = guest.get('rsvpId')

        # Ticket/Order information (for buyers and ticket holders)
        transformed['order_number'] = guest.get('orderNumber')
        transformed['ticket_number'] = guest.get('ticketNumber')

        # Tickets array - flatten to count and details
        tickets = guest.get('tickets', [])
        if tickets:
            transformed['ticket_count'] = len(tickets)
            # Extract ticket definition IDs and numbers
            ticket_def_ids = [t.get('definitionId') for t in tickets if t.get('definitionId')]
            ticket_numbers = [t.get('number') for t in tickets if t.get('number')]
            ticket_names = [t.get('name') for t in tickets if t.get('name')]

            transformed['ticket_definition_ids'] = ', '.join(ticket_def_ids) if ticket_def_ids else None
            transformed['ticket_numbers'] = ', '.join(ticket_numbers) if ticket_numbers else None
            transformed['ticket_names'] = ', '.join(ticket_names) if ticket_names else None

            # Primary ticket info (first ticket)
            if tickets:
                first_ticket = tickets[0]
                transformed['primary_ticket_name'] = first_ticket.get('name')
                transformed['primary_ticket_definition_id'] = first_ticket.get('definitionId')
                transformed['primary_ticket_number'] = first_ticket.get('number')
        else:
            transformed['ticket_count'] = 0
            transformed['ticket_definition_ids'] = None
            transformed['ticket_numbers'] = None
            transformed['ticket_names'] = None
            transformed['primary_ticket_name'] = None
            transformed['primary_ticket_definition_id'] = None
            transformed['primary_ticket_number'] = None

        # Attendance status
        transformed['attendance_status'] = guest.get('attendanceStatus')

        # Additional details (Wix populates this on guest records that have a
        # real order behind them). It carries the canonical paid-vs-free
        # signal that the rest of the API redacts:
        #   - order_status: 'PAID' | 'FREE' | 'UNKNOW_ORDER_STATUS' | None
        #     (Wix's spelling of UNKNOW is intentional, not our typo)
        #   - rsvp_status:  'YES' | 'UNKNOWN_RSVP_STATUS' | None
        #   - additional_details_archived: bool | None
        # When the field block is missing entirely (older guests, anonymized
        # records), all three are None - downstream code should treat that as
        # "unknown" rather than "not free".
        additional_details = guest.get('additionalDetails') or {}
        transformed['order_status'] = additional_details.get('orderStatus')
        transformed['rsvp_status'] = additional_details.get('rsvpStatus')
        transformed['additional_details_archived'] = additional_details.get('archived')

        # Secondary language
        transformed['secondary_language_code'] = guest.get('secondaryLanguageCode')

        # Dates
        created = guest.get('createdDate')
        updated = guest.get('updatedDate')

        if created:
            created_date, created_time = BaseTransformer.extract_date_and_time(created)
            transformed['created_date'] = created_date
            transformed['created_time'] = created_time
            transformed['created_datetime'] = created
        else:
            transformed['created_date'] = None
            transformed['created_time'] = None
            transformed['created_datetime'] = None

        if updated:
            updated_date, updated_time = BaseTransformer.extract_date_and_time(updated)
            transformed['updated_date'] = updated_date
            transformed['updated_time'] = updated_time
            transformed['updated_datetime'] = updated
        else:
            transformed['updated_date'] = None
            transformed['updated_time'] = None
            transformed['updated_datetime'] = None

        # Guest details (only present when fieldsets includes GUEST_DETAILS)
        guest_details = guest.get('guestDetails', {})
        if guest_details:
            # Name
            name = guest_details.get('name', {})
            transformed['first_name'] = name.get('first')
            transformed['last_name'] = name.get('last')

            # Full name (combined)
            if transformed['first_name'] or transformed['last_name']:
                parts = [p for p in [transformed['first_name'], transformed['last_name']] if p]
                transformed['full_name'] = ' '.join(parts)
            else:
                transformed['full_name'] = None

            # Email
            transformed['email'] = guest_details.get('email')

            # Phone
            transformed['phone'] = guest_details.get('phone')

            # Check-in status
            transformed['checked_in'] = guest_details.get('checkedIn', False)

            # Form responses (custom fields from event registration form)
            form_responses = guest_details.get('formResponse', {}).get('inputValues', [])
            if form_responses:
                # Store count of custom responses
                transformed['custom_field_count'] = len(form_responses)

                # Extract a few common custom fields (you may want to customize this)
                for response in form_responses:
                    field_name = response.get('inputName', '').lower()
                    value = response.get('value')

                    # Map common custom fields
                    if 'phone' in field_name and not transformed.get('phone'):
                        transformed['phone'] = value
                    elif 'company' in field_name or 'organization' in field_name:
                        transformed['company'] = value
                    elif 'dietary' in field_name or 'allerg' in field_name:
                        transformed['dietary_notes'] = value
                    elif 'comment' in field_name or 'note' in field_name or 'message' in field_name:
                        transformed['guest_notes'] = value
            else:
                transformed['custom_field_count'] = 0

            # Member information (if guest is a site member)
            member_info = guest_details.get('member', {})
            if member_info:
                transformed['is_member'] = True
                transformed['member_id'] = member_info.get('id')
            else:
                transformed['is_member'] = False
                transformed['member_id'] = None

        else:
            # No guest details available (fieldsets not requested)
            transformed['first_name'] = None
            transformed['last_name'] = None
            transformed['full_name'] = None
            transformed['email'] = None
            transformed['phone'] = None
            transformed['checked_in'] = None
            transformed['custom_field_count'] = 0
            transformed['is_member'] = False
            transformed['member_id'] = None

        return transformed

    @staticmethod
    def transform_guests(guests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple guests.

        Args:
            guests: List of raw guest data from Wix API

        Returns:
            List of flattened guest data
        """
        transformed_guests = []

        for guest in guests:
            try:
                transformed = GuestsTransformer.transform_guest(guest)
                transformed_guests.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming guest {guest.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Transformed {len(transformed_guests)} guests")
        return transformed_guests

    @staticmethod
    def enrich_with_contact_data(
        transformed_guests: List[Dict[str, Any]],
        contacts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich guest data with contact information (names, emails, phones).

        IMPORTANT: The Wix Guests API does NOT return guestDetails with name/email/phone,
        so we need to join with Contacts data using the contactId field.

        Args:
            transformed_guests: List of transformed guest dictionaries
            contacts: List of raw contact data from Wix Contacts API

        Returns:
            List of enriched guest dictionaries with contact info populated

        Example:
            >>> guests = GuestsTransformer.transform_guests(raw_guests)
            >>> enriched = GuestsTransformer.enrich_with_contact_data(guests, raw_contacts)
        """
        # Build contact lookup dictionary: contactId -> contact data
        contact_lookup = {}
        for contact in contacts:
            contact_id = contact.get('id')
            if contact_id:
                # Extract relevant contact fields
                info = contact.get('info', {})
                name = info.get('name', {})
                emails = info.get('emails', {}).get('items', [])
                phones = info.get('phones', {}).get('items', [])

                contact_lookup[contact_id] = {
                    'first_name': name.get('first'),
                    'last_name': name.get('last'),
                    'email': emails[0].get('email') if emails else None,
                    'phone': phones[0].get('phone') if phones else None
                }

        # Enrich each guest with contact data
        enriched_count = 0
        for guest in transformed_guests:
            contact_id = guest.get('contact_id')
            if contact_id and contact_id in contact_lookup:
                contact_data = contact_lookup[contact_id]

                # Only populate if guest doesn't already have this data
                # (in case API ever starts returning guestDetails)
                if not guest.get('first_name'):
                    guest['first_name'] = contact_data['first_name']
                if not guest.get('last_name'):
                    guest['last_name'] = contact_data['last_name']
                if not guest.get('email'):
                    guest['email'] = contact_data['email']
                if not guest.get('phone'):
                    guest['phone'] = contact_data['phone']

                # Rebuild full_name if we added names
                if guest['first_name'] or guest['last_name']:
                    parts = [p for p in [guest['first_name'], guest['last_name']] if p]
                    guest['full_name'] = ' '.join(parts) if parts else None

                enriched_count += 1

        logger.info(f"Enriched {enriched_count}/{len(transformed_guests)} guests with contact data")

        return transformed_guests

    @staticmethod
    def save_to_csv(guests: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """
        Transform guests and save directly to CSV.

        Args:
            guests: List of raw guest data
            output_path: Path to output CSV file
            encoding: File encoding (default: 'utf-8-sig' for Excel compatibility)
            **kwargs: Additional arguments to pass to pandas.to_csv()
        """
        transformed = GuestsTransformer.transform_guests(guests)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
