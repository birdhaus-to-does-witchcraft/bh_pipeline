"""
Transactions/Orders data transformer.

Transforms raw Wix eCommerce Orders and Transactions API data into clean, analysis-ready format.
Handles order information, payment details, and transaction history.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class TransactionsTransformer(BaseTransformer):
    """Transform raw Wix orders and transactions data into clean, flattened format."""

    @staticmethod
    def transform_order(order: Dict[str, Any], transactions: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transform a single order from raw API format to flattened format.

        Args:
            order: Raw order data from Wix API
            transactions: Optional list of transactions for this order

        Returns:
            Flattened order data suitable for CSV export
        """
        transformed = {}

        # Basic order fields
        transformed['order_id'] = order.get('id')
        transformed['order_number'] = order.get('number')
        transformed['checkout_id'] = order.get('checkoutId')

        # Buyer information
        buyer_info = order.get('buyerInfo', {})
        transformed['buyer_id'] = buyer_info.get('id')
        transformed['buyer_email'] = buyer_info.get('email')
        transformed['buyer_first_name'] = buyer_info.get('firstName')
        transformed['buyer_last_name'] = buyer_info.get('lastName')
        transformed['buyer_phone'] = buyer_info.get('phone')

        # Full buyer name
        if transformed['buyer_first_name'] or transformed['buyer_last_name']:
            parts = [p for p in [transformed['buyer_first_name'], transformed['buyer_last_name']] if p]
            transformed['buyer_full_name'] = ' '.join(parts)
        else:
            transformed['buyer_full_name'] = None

        # Buyer language
        transformed['buyer_language'] = order.get('buyerLanguage')

        # Billing information
        billing_info = order.get('billingInfo', {})
        billing_address = billing_info.get('address', {})

        transformed['billing_address'] = billing_address.get('formatted')
        transformed['billing_city'] = billing_address.get('city')
        transformed['billing_country'] = billing_address.get('country')
        transformed['billing_subdivision'] = billing_address.get('subdivision')  # State/Province
        transformed['billing_postal_code'] = billing_address.get('postalCode')

        # Payment details from order
        payment_status = order.get('paymentStatus')
        transformed['payment_status'] = payment_status  # PAID, NOT_PAID, PENDING, etc.

        # Fulfillment information
        fulfillment_status = order.get('fulfillmentStatus')
        transformed['fulfillment_status'] = fulfillment_status  # FULFILLED, NOT_FULFILLED, PARTIALLY_FULFILLED

        # Order totals
        pricing_summary = order.get('pricingSummary', {})
        subtotal = pricing_summary.get('subtotal', {})
        total = pricing_summary.get('total', {})
        tax = pricing_summary.get('tax', {})
        shipping = pricing_summary.get('shipping', {})
        discount = pricing_summary.get('discount', {})

        transformed['currency'] = order.get('currency')
        transformed['subtotal_amount'] = subtotal.get('amount')
        transformed['subtotal_formatted'] = subtotal.get('formattedAmount')

        transformed['total_amount'] = total.get('amount')
        transformed['total_formatted'] = total.get('formattedAmount')

        transformed['tax_amount'] = tax.get('amount')
        transformed['tax_formatted'] = tax.get('formattedAmount')

        transformed['shipping_amount'] = shipping.get('amount')
        transformed['shipping_formatted'] = shipping.get('formattedAmount')

        transformed['discount_amount'] = discount.get('amount')
        transformed['discount_formatted'] = discount.get('formattedAmount')

        # Line items (products purchased)
        line_items = order.get('lineItems', [])
        transformed['line_item_count'] = len(line_items)

        if line_items:
            # Extract product names and IDs
            product_names = []
            product_ids = []
            quantities = []

            for item in line_items:
                product_name = item.get('productName', {})
                if isinstance(product_name, dict):
                    name = product_name.get('original', product_name.get('translated', ''))
                else:
                    name = str(product_name)

                if name:
                    product_names.append(name)

                catalog_ref = item.get('catalogReference', {})
                if catalog_ref.get('catalogItemId'):
                    product_ids.append(catalog_ref['catalogItemId'])

                quantities.append(str(item.get('quantity', 1)))

            transformed['product_names'] = ', '.join(product_names) if product_names else None
            transformed['product_ids'] = ', '.join(product_ids) if product_ids else None
            transformed['quantities'] = ', '.join(quantities) if quantities else None

            # Primary product (first item)
            first_item = line_items[0]
            product_name = first_item.get('productName', {})
            if isinstance(product_name, dict):
                transformed['primary_product_name'] = product_name.get('original', product_name.get('translated'))
            else:
                transformed['primary_product_name'] = str(product_name)

            transformed['primary_product_price'] = first_item.get('price', {}).get('amount')
            transformed['primary_product_quantity'] = first_item.get('quantity', 1)
        else:
            transformed['product_names'] = None
            transformed['product_ids'] = None
            transformed['quantities'] = None
            transformed['primary_product_name'] = None
            transformed['primary_product_price'] = None
            transformed['primary_product_quantity'] = None

        # Applied discounts/coupons
        applied_discounts = order.get('appliedDiscounts', [])
        if applied_discounts:
            discount_codes = [d.get('coupon', {}).get('code') for d in applied_discounts if d.get('coupon', {}).get('code')]
            transformed['discount_codes'] = ', '.join(discount_codes) if discount_codes else None
            transformed['discount_count'] = len(applied_discounts)
        else:
            transformed['discount_codes'] = None
            transformed['discount_count'] = 0

        # Channel information (where order was placed)
        channel_info = order.get('channelInfo', {})
        transformed['channel_type'] = channel_info.get('type')  # WEB, MOBILE, etc.

        # Shipping information
        shipping_info = order.get('shippingInfo', {})
        logistics = shipping_info.get('logistics', {})

        if logistics:
            shipping_dest = logistics.get('shippingDestination', {})
            contact_details = shipping_dest.get('contactDetails', {})

            transformed['shipping_first_name'] = contact_details.get('firstName')
            transformed['shipping_last_name'] = contact_details.get('lastName')
            transformed['shipping_phone'] = contact_details.get('phone')

            # Shipping address
            ship_address = shipping_dest.get('address', {})
            transformed['shipping_address'] = ship_address.get('formatted')
            transformed['shipping_city'] = ship_address.get('city')
            transformed['shipping_country'] = ship_address.get('country')
            transformed['shipping_subdivision'] = ship_address.get('subdivision')
            transformed['shipping_postal_code'] = ship_address.get('postalCode')

            # Shipping option
            selected_option = logistics.get('selectedCarrierServiceOption', {})
            transformed['shipping_method'] = selected_option.get('title')
            transformed['shipping_carrier'] = selected_option.get('code')
        else:
            transformed['shipping_first_name'] = None
            transformed['shipping_last_name'] = None
            transformed['shipping_phone'] = None
            transformed['shipping_address'] = None
            transformed['shipping_city'] = None
            transformed['shipping_country'] = None
            transformed['shipping_subdivision'] = None
            transformed['shipping_postal_code'] = None
            transformed['shipping_method'] = None
            transformed['shipping_carrier'] = None

        # Dates
        created = order.get('createdDate')
        updated = order.get('updatedDate')

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

        # Transaction information (if provided)
        if transactions:
            transformed['transaction_count'] = len(transactions)

            # Summary of transaction statuses
            transaction_statuses = [t.get('status') for t in transactions if t.get('status')]
            transformed['transaction_statuses'] = ', '.join(set(transaction_statuses)) if transaction_statuses else None

            # Primary transaction (first or most recent)
            if transactions:
                primary_txn = transactions[0]
                transformed['primary_transaction_id'] = primary_txn.get('id')
                transformed['primary_transaction_status'] = primary_txn.get('status')
                transformed['primary_payment_method'] = primary_txn.get('paymentMethod')

                # Transaction amounts
                amounts = primary_txn.get('amounts', {})
                transformed['transaction_amount'] = amounts.get('total')
                transformed['transaction_currency'] = primary_txn.get('currency')
        else:
            transformed['transaction_count'] = 0
            transformed['transaction_statuses'] = None
            transformed['primary_transaction_id'] = None
            transformed['primary_transaction_status'] = None
            transformed['primary_payment_method'] = None
            transformed['transaction_amount'] = None
            transformed['transaction_currency'] = None

        # Custom fields
        custom_fields = order.get('customFields', [])
        if custom_fields:
            transformed['custom_field_count'] = len(custom_fields)
            # You can extract specific custom fields here if needed
        else:
            transformed['custom_field_count'] = 0

        # Archive status
        transformed['archived'] = order.get('archived', False)

        # Activity counters
        activities = order.get('activities', [])
        transformed['activity_count'] = len(activities)

        return transformed

    @staticmethod
    def transform_orders(orders: List[Dict[str, Any]], transactions_by_order: Dict[str, List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Transform multiple orders.

        Args:
            orders: List of raw order data from Wix API
            transactions_by_order: Optional dict mapping order IDs to their transactions

        Returns:
            List of flattened order data
        """
        transformed_orders = []

        for order in orders:
            try:
                order_id = order.get('id')
                order_transactions = transactions_by_order.get(order_id, []) if transactions_by_order else None

                transformed = TransactionsTransformer.transform_order(order, order_transactions)
                transformed_orders.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming order {order.get('number', 'unknown')}: {e}")
                continue

        logger.info(f"Transformed {len(transformed_orders)} orders")
        return transformed_orders

    @staticmethod
    def save_to_csv(orders: List[Dict[str, Any]], output_path: str,
                   transactions_by_order: Dict[str, List[Dict[str, Any]]] = None,
                   encoding: str = 'utf-8-sig', **kwargs):
        """
        Transform orders and save directly to CSV.

        Args:
            orders: List of raw order data
            output_path: Path to output CSV file
            transactions_by_order: Optional dict mapping order IDs to their transactions
            encoding: File encoding (default: 'utf-8-sig' for Excel compatibility)
            **kwargs: Additional arguments to pass to pandas.to_csv()
        """
        transformed = TransactionsTransformer.transform_orders(orders, transactions_by_order)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
