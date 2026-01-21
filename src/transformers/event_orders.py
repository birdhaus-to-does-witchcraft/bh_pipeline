"""
Event Orders data transformer.

Transforms raw Wix Event Orders API data into clean, analysis-ready format.
Handles individual ticket orders from events.

Note: This transformer is designed for the Events Orders API (/events/v1/orders),
NOT the eCommerce Orders API. The data structure is specific to event ticketing.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class EventOrdersTransformer(BaseTransformer):
    """Transform raw Wix Event Orders data into clean, flattened format."""

    @staticmethod
    def transform_order(order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single event order from raw API format to flattened format.

        Args:
            order: Raw order data from Wix Events Orders API

        Returns:
            Flattened order data suitable for CSV export
        """
        transformed = {}

        # Basic order fields
        transformed['order_number'] = order.get('orderNumber')
        transformed['event_id'] = order.get('eventId')
        transformed['reservation_id'] = order.get('reservationId') or None
        transformed['snapshot_id'] = order.get('snapshotId') or None

        # Customer/Contact information
        transformed['contact_id'] = order.get('contactId')
        transformed['member_id'] = order.get('memberId') or None
        transformed['first_name'] = order.get('firstName') or None
        transformed['last_name'] = order.get('lastName') or None
        transformed['email'] = order.get('email') or None
        transformed['full_name'] = order.get('fullName') or None

        # Order status
        transformed['status'] = order.get('status')
        transformed['confirmed'] = order.get('confirmed', False)
        transformed['archived'] = order.get('archived', False)
        transformed['anonymized'] = order.get('anonymized', False)

        # Channel and method
        transformed['channel'] = order.get('channel')  # ONLINE, OFFLINE
        transformed['method'] = order.get('method') or None

        # Ticket summary
        transformed['tickets_quantity'] = order.get('ticketsQuantity', 0)
        transformed['tickets_pdf'] = order.get('ticketsPdf') or None
        transformed['fully_checked_in'] = order.get('fullyCheckedIn', False)

        # Extract ticket details from tickets array
        tickets = order.get('tickets', [])
        transformed['ticket_count'] = len(tickets)

        if tickets:
            ticket_names = []
            ticket_prices = []
            ticket_numbers = []

            for ticket in tickets:
                # Ticket name
                name = ticket.get('ticketName') or ticket.get('name', '')
                if name:
                    ticket_names.append(name)

                # Ticket number
                number = ticket.get('ticketNumber') or ticket.get('number', '')
                if number:
                    ticket_numbers.append(str(number))

                # Ticket price
                price = ticket.get('price', {})
                if isinstance(price, dict):
                    amount = price.get('amount') or price.get('value')
                    if amount:
                        ticket_prices.append(str(amount))
                elif price:
                    ticket_prices.append(str(price))

            transformed['ticket_names'] = ', '.join(ticket_names) if ticket_names else None
            transformed['ticket_numbers'] = ', '.join(ticket_numbers) if ticket_numbers else None
            transformed['ticket_prices'] = ', '.join(ticket_prices) if ticket_prices else None
        else:
            transformed['ticket_names'] = None
            transformed['ticket_numbers'] = None
            transformed['ticket_prices'] = None

        # Transaction/Payment information
        transformed['transaction_id'] = order.get('transactionId') or None

        payment_details = order.get('paymentDetails', {})
        transaction = payment_details.get('transaction', {})

        transformed['payment_method'] = transaction.get('method') or None
        transformed['payment_transaction_id'] = transaction.get('transactionId') or None
        transformed['scheduled_action'] = transaction.get('scheduledAction') or None

        # Price summary (if available in payment details)
        price_summary = payment_details.get('priceSummary', {})
        if price_summary:
            transformed['subtotal'] = price_summary.get('subtotal', {}).get('amount') if isinstance(price_summary.get('subtotal'), dict) else price_summary.get('subtotal')
            transformed['total'] = price_summary.get('total', {}).get('amount') if isinstance(price_summary.get('total'), dict) else price_summary.get('total')
            transformed['tax'] = price_summary.get('tax', {}).get('amount') if isinstance(price_summary.get('tax'), dict) else price_summary.get('tax')
            transformed['discount'] = price_summary.get('discount', {}).get('amount') if isinstance(price_summary.get('discount'), dict) else price_summary.get('discount')
            transformed['fees'] = price_summary.get('fees', {}).get('amount') if isinstance(price_summary.get('fees'), dict) else price_summary.get('fees')
            transformed['currency'] = price_summary.get('currency')
        else:
            transformed['subtotal'] = None
            transformed['total'] = None
            transformed['tax'] = None
            transformed['discount'] = None
            transformed['fees'] = None
            transformed['currency'] = None

        # Gift card payment details
        gift_card_details = order.get('giftCardPaymentDetails', [])
        transformed['gift_card_count'] = len(gift_card_details) if gift_card_details else 0

        # Available actions
        available_actions = order.get('availableActions', [])
        transformed['available_actions'] = ', '.join(available_actions) if available_actions else None

        # Created/Updated dates (if present in API response)
        created = order.get('created') or order.get('createdDate')
        updated = order.get('updated') or order.get('updatedDate')

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

        return transformed

    @staticmethod
    def transform_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple event orders.

        Args:
            orders: List of raw order data from Wix Events Orders API

        Returns:
            List of flattened order data
        """
        transformed_orders = []

        for order in orders:
            try:
                transformed = EventOrdersTransformer.transform_order(order)
                transformed_orders.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming order {order.get('orderNumber', 'unknown')}: {e}")
                continue

        logger.info(f"Transformed {len(transformed_orders)} event orders")
        return transformed_orders

    @staticmethod
    def save_to_csv(orders: List[Dict[str, Any]], output_path: str,
                    encoding: str = 'utf-8-sig', **kwargs):
        """
        Transform event orders and save directly to CSV.

        Args:
            orders: List of raw order data from Wix Events Orders API
            output_path: Path to output CSV file
            encoding: File encoding (default: 'utf-8-sig' for Excel compatibility)
            **kwargs: Additional arguments to pass to pandas.to_csv()
        """
        transformed = EventOrdersTransformer.transform_orders(orders)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
