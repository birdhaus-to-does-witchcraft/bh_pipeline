"""
Coupons data transformer.

Transforms raw Wix Coupons API data into clean, analysis-ready format.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class CouponsTransformer(BaseTransformer):
    """Transform raw Wix coupon data into clean, flattened format."""

    @staticmethod
    def transform_coupon(coupon: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single coupon record."""
        transformed = {}

        transformed['coupon_id'] = coupon.get('id')
        transformed['name'] = coupon.get('name')
        transformed['code'] = coupon.get('code')
        transformed['active'] = coupon.get('active')
        transformed['expired'] = coupon.get('expired')

        # Specification (discount type and scope)
        spec = coupon.get('specification', {})
        transformed['coupon_type'] = spec.get('type')
        transformed['display_name'] = spec.get('name')

        # Discount details (one of these will be present)
        if spec.get('moneyOffAmount'):
            transformed['discount_type'] = 'money_off'
            transformed['discount_value'] = spec['moneyOffAmount']
        elif spec.get('percentOffRate'):
            transformed['discount_type'] = 'percent_off'
            transformed['discount_value'] = spec['percentOffRate']
        elif spec.get('fixedPriceAmount'):
            transformed['discount_type'] = 'fixed_price'
            transformed['discount_value'] = spec['fixedPriceAmount']
        elif spec.get('freeShipping'):
            transformed['discount_type'] = 'free_shipping'
            transformed['discount_value'] = None
        else:
            transformed['discount_type'] = None
            transformed['discount_value'] = None

        # Scope
        scope = spec.get('scope', {})
        transformed['scope_namespace'] = scope.get('namespace')

        scope_group = scope.get('group', {})
        transformed['scope_group_name'] = scope_group.get('name')
        transformed['scope_entity_id'] = scope_group.get('entityId')

        # Minimums
        transformed['minimum_subtotal'] = spec.get('minimumSubtotal')

        # Usage limits
        transformed['limited_to_one_item'] = spec.get('limitedToOneItem')
        transformed['applies_to_lowest_price'] = spec.get('appliesToLowestPriceItem')
        transformed['limit_per_customer'] = coupon.get('limitPerCustomer')

        # Usage stats
        transformed['number_of_usages'] = coupon.get('numberOfUsages')

        # Dates
        date_created = coupon.get('dateCreated')
        if date_created:
            cd, ct = BaseTransformer.extract_date_and_time(date_created)
            transformed['created_date'] = cd
            transformed['created_time'] = ct
        else:
            transformed['created_date'] = None
            transformed['created_time'] = None

        start_time = spec.get('startTime')
        if start_time:
            sd, st = BaseTransformer.extract_date_and_time(start_time)
            transformed['start_date'] = sd
            transformed['start_time'] = st
        else:
            transformed['start_date'] = None
            transformed['start_time'] = None

        expiration_time = spec.get('expirationTime')
        if expiration_time:
            ed, et = BaseTransformer.extract_date_and_time(expiration_time)
            transformed['expiration_date'] = ed
            transformed['expiration_time'] = et
        else:
            transformed['expiration_date'] = None
            transformed['expiration_time'] = None

        return transformed

    @staticmethod
    def transform_coupons(coupons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple coupon records."""
        transformed_coupons = []
        for coupon in coupons:
            try:
                transformed_coupons.append(CouponsTransformer.transform_coupon(coupon))
            except Exception as e:
                logger.error(f"Error transforming coupon {coupon.get('id', 'unknown')}: {e}")
        logger.info(f"Transformed {len(transformed_coupons)} coupons")
        return transformed_coupons

    @staticmethod
    def save_to_csv(coupons: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """Transform coupons and save to CSV."""
        transformed = CouponsTransformer.transform_coupons(coupons)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
