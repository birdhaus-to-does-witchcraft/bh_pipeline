"""
RSVPs data transformer.

Transforms raw Wix RSVP API data into clean, analysis-ready format.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class RSVPsTransformer(BaseTransformer):
    """Transform raw Wix RSVP data into clean, flattened format."""

    @staticmethod
    def transform_rsvp(rsvp: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single RSVP record."""
        transformed = {}

        transformed['rsvp_id'] = rsvp.get('id')
        transformed['event_id'] = rsvp.get('eventId')
        transformed['contact_id'] = rsvp.get('contactId')
        transformed['member_id'] = rsvp.get('memberId')

        transformed['rsvp_status'] = rsvp.get('rsvpStatus')
        transformed['check_in_status'] = rsvp.get('checkInStatus')

        # Guest info
        transformed['first_name'] = rsvp.get('firstName')
        transformed['last_name'] = rsvp.get('lastName')
        transformed['email'] = rsvp.get('email')

        # Guest names (may be a list)
        guest_names = rsvp.get('guestNames', [])
        transformed['guest_names'] = '; '.join(guest_names) if guest_names else None
        transformed['additional_guests'] = rsvp.get('additionalGuests', 0)
        transformed['total_guests'] = rsvp.get('totalGuests', 1)

        # Form response (custom registration fields)
        form_response = rsvp.get('formResponse', {})
        input_values = form_response.get('inputValues', [])
        for iv in input_values:
            field_name = iv.get('inputName', '').replace(' ', '_').lower()
            if field_name:
                transformed[f'form_{field_name}'] = iv.get('value') or iv.get('values', '')

        # Dates
        created = rsvp.get('createdDate') or rsvp.get('_createdDate')
        updated = rsvp.get('updatedDate') or rsvp.get('_updatedDate')

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
    def transform_rsvps(rsvps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple RSVP records."""
        transformed_rsvps = []
        for rsvp in rsvps:
            try:
                transformed_rsvps.append(RSVPsTransformer.transform_rsvp(rsvp))
            except Exception as e:
                logger.error(f"Error transforming RSVP {rsvp.get('id', 'unknown')}: {e}")
        logger.info(f"Transformed {len(transformed_rsvps)} RSVPs")
        return transformed_rsvps

    @staticmethod
    def save_to_csv(rsvps: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """Transform RSVPs and save to CSV."""
        transformed = RSVPsTransformer.transform_rsvps(rsvps)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
