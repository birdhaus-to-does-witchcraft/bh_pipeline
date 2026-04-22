"""
Ticket Definitions data transformer.

Flattens Wix Ticket Definitions V3 records into CSV-friendly rows.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class TicketDefinitionsTransformer(BaseTransformer):
    """Transform raw Wix ticket definition data into clean, flattened format."""

    @staticmethod
    def transform_definition(definition: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single ticket definition record."""
        transformed: Dict[str, Any] = {}

        transformed['definition_id'] = definition.get('id')
        transformed['event_id'] = definition.get('eventId')
        transformed['revision'] = definition.get('revision')
        transformed['name'] = definition.get('name')
        transformed['description'] = definition.get('description')
        transformed['hidden'] = definition.get('hidden')

        # Pricing method
        pricing_method = definition.get('pricingMethod', {})
        transformed['pricing_type'] = pricing_method.get('pricingType')

        fixed_price = pricing_method.get('fixedPrice', {})
        transformed['fixed_price_value'] = fixed_price.get('value')
        transformed['fixed_price_currency'] = fixed_price.get('currency')

        guest_price = pricing_method.get('guestPrice', {})
        transformed['guest_price_value'] = guest_price.get('value')
        transformed['guest_price_currency'] = guest_price.get('currency')

        # Pricing options (multiple price tiers, e.g. early bird vs general admission)
        pricing_options = pricing_method.get('pricingOptions', {}).get('options', [])
        transformed['pricing_options_count'] = len(pricing_options)
        if pricing_options:
            option_names = [o.get('name', '') for o in pricing_options]
            transformed['pricing_option_names'] = '; '.join(filter(None, option_names))
        else:
            transformed['pricing_option_names'] = None

        transformed['free'] = definition.get('free')
        transformed['fee_type'] = definition.get('feeType')

        # Sale period
        sale_period = definition.get('salePeriod', {})
        start_date = sale_period.get('startDate')
        end_date = sale_period.get('endDate')

        if start_date:
            sd, st = BaseTransformer.extract_date_and_time(start_date)
            transformed['sale_start_date'] = sd
            transformed['sale_start_time'] = st
        else:
            transformed['sale_start_date'] = None
            transformed['sale_start_time'] = None

        if end_date:
            ed, et = BaseTransformer.extract_date_and_time(end_date)
            transformed['sale_end_date'] = ed
            transformed['sale_end_time'] = et
        else:
            transformed['sale_end_date'] = None
            transformed['sale_end_time'] = None

        transformed['display_not_on_sale'] = definition.get('displayNotOnSale')
        transformed['sale_status'] = definition.get('saleStatus')

        # Sales details (only present when SALES_DETAILS fieldset requested)
        sales_details = definition.get('salesDetails', {})
        transformed['unsold_count'] = sales_details.get('unsoldCount')
        transformed['sold_count'] = sales_details.get('soldCount')
        transformed['reserved_count'] = sales_details.get('reservedCount')
        transformed['sold_out'] = sales_details.get('soldOut')

        # Limits
        transformed['initial_limit'] = definition.get('initialLimit')
        transformed['actual_limit'] = definition.get('actualLimit')
        transformed['limit_per_checkout'] = definition.get('limitPerCheckout')

        # Dates
        created = definition.get('createdDate') or definition.get('_createdDate')
        updated = definition.get('updatedDate') or definition.get('_updatedDate')

        if created:
            cd, ct = BaseTransformer.extract_date_and_time(created)
            transformed['created_date'] = cd
            transformed['created_time'] = ct
        else:
            transformed['created_date'] = None
            transformed['created_time'] = None

        if updated:
            ud, ut = BaseTransformer.extract_date_and_time(updated)
            transformed['updated_date'] = ud
            transformed['updated_time'] = ut
        else:
            transformed['updated_date'] = None
            transformed['updated_time'] = None

        return transformed

    @staticmethod
    def transform_definitions(definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple ticket definition records."""
        transformed = []
        for definition in definitions:
            try:
                transformed.append(
                    TicketDefinitionsTransformer.transform_definition(definition)
                )
            except Exception as e:
                logger.error(
                    f"Error transforming ticket definition {definition.get('id', 'unknown')}: {e}"
                )
        logger.info(f"Transformed {len(transformed)} ticket definitions")
        return transformed

    @staticmethod
    def save_to_csv(
        definitions: List[Dict[str, Any]],
        output_path: str,
        encoding: str = 'utf-8-sig',
        **kwargs,
    ):
        """Transform ticket definitions and save to CSV."""
        transformed = TicketDefinitionsTransformer.transform_definitions(definitions)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
