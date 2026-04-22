"""
Tickets data transformer.

Transforms raw Wix Tickets V1 API data into clean, analysis-ready format.

NOTE: The Wix Ticket V1 object does NOT include fee or tax fields directly.
Those configurations live on the linked TicketDefinition (template). To get
them, pass a definitions_lookup dict to add joined columns.
"""

import logging
from typing import Any, Dict, List, Optional

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class TicketsTransformer(BaseTransformer):
    """Transform raw Wix sold ticket data into clean, flattened format."""

    @staticmethod
    def transform_ticket(
        ticket: Dict[str, Any],
        definitions_lookup: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Transform a single ticket record.

        Args:
            ticket: Raw ticket dict from Wix Tickets V1 API
            definitions_lookup: Optional {ticket_definition_id: definition_dict} for joining
                fee_type, pricing_type, sale_status, sold_count from the TicketDefinition.
        """
        transformed: Dict[str, Any] = {}

        # Identifiers
        transformed['ticket_number'] = ticket.get('ticketNumber')
        transformed['event_id'] = ticket.get('eventId')
        transformed['order_number'] = ticket.get('orderNumber')
        transformed['ticket_definition_id'] = ticket.get('ticketDefinitionId')

        # Ticket type info
        transformed['ticket_name'] = ticket.get('name')
        transformed['policy'] = ticket.get('policy')
        transformed['free'] = ticket.get('free')
        transformed['archived'] = ticket.get('archived')
        transformed['order_archived'] = ticket.get('orderArchived')

        # Order status
        transformed['order_status'] = ticket.get('orderStatus')

        # Buyer / guest details
        # Note: 'email' is the buyer email; 'guestEmail' is sometimes returned (legacy).
        transformed['order_full_name'] = ticket.get('orderFullName')
        transformed['guest_full_name'] = ticket.get('guestFullName')
        transformed['email'] = ticket.get('email') or ticket.get('guestEmail')
        transformed['member_id'] = ticket.get('memberId')
        transformed['contact_id'] = ticket.get('contactId')

        # Pricing (Money: value is current, amount is deprecated but used as fallback)
        price = ticket.get('price') or {}
        transformed['price_value'] = price.get('value') or price.get('amount')
        transformed['price_currency'] = price.get('currency')

        # Check-in
        check_in = ticket.get('checkIn') or {}
        transformed['checked_in'] = bool(check_in)
        check_in_created = check_in.get('created') if isinstance(check_in, dict) else None
        if check_in_created:
            cd, ct = BaseTransformer.extract_date_and_time(check_in_created)
            transformed['check_in_date'] = cd
            transformed['check_in_time'] = ct
        else:
            transformed['check_in_date'] = None
            transformed['check_in_time'] = None

        transformed['check_in_url'] = ticket.get('checkInUrl')
        transformed['ticket_pdf_url'] = ticket.get('ticketPdfUrl')

        # Form responses (custom registration questions)
        form = ticket.get('form') or {}
        input_values = form.get('inputValues', []) if isinstance(form, dict) else []
        for iv in input_values:
            if not isinstance(iv, dict):
                continue
            input_name = iv.get('inputName') or ''
            safe_key = f"form_{input_name.replace(' ', '_').replace('.', '_').lower()}"
            value = iv.get('value')
            values = iv.get('values')
            if value is not None:
                transformed[safe_key] = value
            elif values:
                transformed[safe_key] = '; '.join(str(v) for v in values)

        # Joined ticket-definition columns (fee_type, pricing_type, sale_status, etc.)
        def_id = ticket.get('ticketDefinitionId')
        if definitions_lookup and def_id and def_id in definitions_lookup:
            definition = definitions_lookup[def_id]
            transformed['def_pricing_type'] = (
                definition.get('pricingMethod', {}).get('pricingType')
            )
            transformed['def_fee_type'] = definition.get('feeType')
            transformed['def_sale_status'] = definition.get('saleStatus')
            sales_details = definition.get('salesDetails', {}) or {}
            transformed['def_sold_count'] = sales_details.get('soldCount')
            transformed['def_sold_out'] = sales_details.get('soldOut')
        else:
            transformed['def_pricing_type'] = None
            transformed['def_fee_type'] = None
            transformed['def_sale_status'] = None
            transformed['def_sold_count'] = None
            transformed['def_sold_out'] = None

        # Dates
        created = ticket.get('createdDate') or ticket.get('_createdDate')
        if created:
            cd, ct = BaseTransformer.extract_date_and_time(created)
            transformed['created_date'] = cd
            transformed['created_time'] = ct
        else:
            transformed['created_date'] = None
            transformed['created_time'] = None

        return transformed

    @staticmethod
    def transform_tickets(
        tickets: List[Dict[str, Any]],
        definitions_lookup: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Transform multiple ticket records, optionally joined with definitions."""
        transformed_tickets = []
        for ticket in tickets:
            try:
                transformed_tickets.append(
                    TicketsTransformer.transform_ticket(ticket, definitions_lookup)
                )
            except Exception as e:
                logger.error(
                    f"Error transforming ticket {ticket.get('ticketNumber', 'unknown')}: {e}"
                )
        logger.info(f"Transformed {len(transformed_tickets)} tickets")
        return transformed_tickets

    @staticmethod
    def save_to_csv(
        tickets: List[Dict[str, Any]],
        output_path: str,
        encoding: str = 'utf-8-sig',
        definitions_lookup: Optional[Dict[str, Dict[str, Any]]] = None,
        **kwargs,
    ):
        """Transform tickets and save to CSV."""
        transformed = TicketsTransformer.transform_tickets(tickets, definitions_lookup)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
