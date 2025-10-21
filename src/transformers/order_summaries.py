"""
Order summaries data transformer.

Transforms sales summary data from Wix Events Orders API into clean, analysis-ready format.
Includes total sales, revenue, fees, and ticket counts per event.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class OrderSummariesTransformer(BaseTransformer):
    """Transform order summary sales data into clean, flattened format."""

    @staticmethod
    def transform_summary(event_id: str, event_title: str, summary_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single event's sales summary from raw API format to flattened format.

        Args:
            event_id: The event ID
            event_title: The event title (from Events API)
            summary_response: Raw summary response from Orders API

        Returns:
            Flattened summary data suitable for CSV export
        """
        transformed = {}

        # Event identification
        transformed['event_id'] = event_id
        transformed['event_title'] = event_title

        # Extract sales data (may be empty array if no sales)
        sales_array = summary_response.get('sales', [])

        if sales_array:
            sales = sales_array[0]

            # Total sales (including fees)
            total = sales.get('total', {})
            transformed['total_sales_amount'] = total.get('amount')
            transformed['total_sales_currency'] = total.get('currency')

            # Revenue (after Wix fees)
            revenue = sales.get('revenue', {})
            transformed['revenue_amount'] = revenue.get('amount')
            transformed['revenue_currency'] = revenue.get('currency')

            # Calculate fees (difference between total and revenue)
            if total.get('amount') and revenue.get('amount'):
                total_amt = float(total.get('amount', 0))
                revenue_amt = float(revenue.get('amount', 0))
                fees = total_amt - revenue_amt
                transformed['wix_fees_amount'] = f"{fees:.2f}"

                # Calculate fee percentage
                if total_amt > 0:
                    fee_pct = (fees / total_amt) * 100
                    transformed['wix_fees_percentage'] = f"{fee_pct:.2f}"
                else:
                    transformed['wix_fees_percentage'] = "0.00"
            else:
                transformed['wix_fees_amount'] = None
                transformed['wix_fees_percentage'] = None

            # Order and ticket counts
            transformed['total_orders'] = sales.get('totalOrders', 0)
            transformed['total_tickets'] = sales.get('totalTickets', 0)

            # Calculate average ticket price
            if sales.get('totalTickets', 0) > 0 and total.get('amount'):
                avg_price = float(total.get('amount', 0)) / sales.get('totalTickets', 0)
                transformed['avg_ticket_price'] = f"{avg_price:.2f}"
            else:
                transformed['avg_ticket_price'] = None

            # Flag indicating sales exist
            transformed['has_sales'] = True

        else:
            # No sales for this event
            transformed['total_sales_amount'] = None
            transformed['total_sales_currency'] = None
            transformed['revenue_amount'] = None
            transformed['revenue_currency'] = None
            transformed['wix_fees_amount'] = None
            transformed['wix_fees_percentage'] = None
            transformed['total_orders'] = 0
            transformed['total_tickets'] = 0
            transformed['avg_ticket_price'] = None
            transformed['has_sales'] = False

        return transformed

    @staticmethod
    def transform_summaries(events: List[Dict[str, Any]], summary_responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple event summaries.

        Args:
            events: List of event data (from Events API) with id and title
            summary_responses: List of summary responses (from Orders API) in same order

        Returns:
            List of flattened summary data
        """
        transformed_summaries = []

        for i, event in enumerate(events):
            try:
                event_id = event.get('id')
                event_title = event.get('title', 'Untitled Event')

                # Get corresponding summary response
                summary_response = summary_responses[i] if i < len(summary_responses) else {'sales': []}

                transformed = OrderSummariesTransformer.transform_summary(
                    event_id,
                    event_title,
                    summary_response
                )
                transformed_summaries.append(transformed)

            except Exception as e:
                logger.error(f"Error transforming summary for event {event.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Transformed {len(transformed_summaries)} order summaries")
        return transformed_summaries

    @staticmethod
    def save_to_csv(events: List[Dict[str, Any]], summary_responses: List[Dict[str, Any]],
                    output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """
        Transform summaries and save directly to CSV.

        Args:
            events: List of event data
            summary_responses: List of summary responses
            output_path: Path to output CSV file
            encoding: File encoding (default: 'utf-8-sig' for Excel compatibility)
            **kwargs: Additional arguments to pass to pandas.to_csv()
        """
        transformed = OrderSummariesTransformer.transform_summaries(events, summary_responses)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
