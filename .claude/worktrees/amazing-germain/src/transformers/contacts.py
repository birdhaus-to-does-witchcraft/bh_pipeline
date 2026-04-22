"""
Contacts data transformer.

Transforms raw Wix Contacts API data into clean, analysis-ready format.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class ContactsTransformer(BaseTransformer):
    """Transform raw Wix contacts data into clean, flattened format."""

    @staticmethod
    def transform_contact(contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single contact from raw API format to flattened format.

        Args:
            contact: Raw contact data from Wix API

        Returns:
            Flattened contact data suitable for CSV export
        """
        transformed = {}

        # Basic fields
        transformed['contact_id'] = contact.get('id')
        transformed['revision'] = contact.get('revision')

        # Dates
        created = contact.get('createdDate')
        updated = contact.get('updatedDate')

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

        # Primary info
        primary_info = contact.get('primaryInfo', {})
        transformed['primary_email'] = primary_info.get('email')

        # Detailed info
        info = contact.get('info', {})

        # Name
        name = info.get('name', {})
        transformed['first_name'] = name.get('first')
        transformed['last_name'] = name.get('last')

        # Full name (combined)
        if transformed['first_name'] or transformed['last_name']:
            parts = [p for p in [transformed['first_name'], transformed['last_name']] if p]
            transformed['full_name'] = ' '.join(parts)
        else:
            transformed['full_name'] = None

        # Emails (may have multiple)
        emails_info = info.get('emails', {}).get('items', [])
        if emails_info:
            # Get primary email
            primary_email_obj = next((e for e in emails_info if e.get('primary')), emails_info[0] if emails_info else None)
            if primary_email_obj:
                transformed['email'] = primary_email_obj.get('email')
                transformed['email_tag'] = primary_email_obj.get('tag')

            # Count total emails
            transformed['email_count'] = len(emails_info)
        else:
            transformed['email'] = transformed['primary_email']  # Fallback
            transformed['email_tag'] = None
            transformed['email_count'] = 1 if transformed['primary_email'] else 0

        # Picture
        picture = contact.get('picture', {})
        transformed['picture_url'] = picture.get('url')
        transformed['picture_width'] = picture.get('width')
        transformed['picture_height'] = picture.get('height')

        # Email subscription status
        primary_email_obj = contact.get('primaryEmail', {})
        transformed['subscription_status'] = primary_email_obj.get('subscriptionStatus')
        transformed['deliverability_status'] = primary_email_obj.get('deliverabilityStatus')

        # Member info (if contact is a site member)
        member_info = contact.get('memberInfo', {})
        if member_info:
            transformed['is_member'] = True
            transformed['member_id'] = member_info.get('memberId')
            transformed['member_status'] = member_info.get('status')
            transformed['member_email_verified'] = member_info.get('emailVerified')

            # Signup date
            signup_date = member_info.get('signupDate')
            if signup_date:
                signup_d, signup_t = BaseTransformer.extract_date_and_time(signup_date)
                transformed['signup_date'] = signup_d
                transformed['signup_time'] = signup_t
            else:
                transformed['signup_date'] = None
                transformed['signup_time'] = None

            # Profile info
            profile_info = member_info.get('profileInfo', {})
            transformed['profile_nickname'] = profile_info.get('nickname')
            transformed['profile_privacy'] = profile_info.get('privacyStatus')

            # User role
            user_info = member_info.get('userInfo', {})
            transformed['user_role'] = user_info.get('role')
            transformed['user_id'] = user_info.get('userId')
        else:
            transformed['is_member'] = False
            transformed['member_id'] = None
            transformed['member_status'] = None
            transformed['member_email_verified'] = None
            transformed['signup_date'] = None
            transformed['signup_time'] = None
            transformed['profile_nickname'] = None
            transformed['profile_privacy'] = None
            transformed['user_role'] = None
            transformed['user_id'] = None

        # Source
        source = contact.get('source', {})
        transformed['source_type'] = source.get('sourceType')
        transformed['source_app_id'] = source.get('appId')

        # Extended fields (custom data)
        extended_fields = info.get('extendedFields', {}).get('items', {})
        if extended_fields:
            # Extract a few key extended fields
            transformed['display_name_first_last'] = extended_fields.get('contacts.displayByFirstName')
            transformed['display_name_last_first'] = extended_fields.get('contacts.displayByLastName')
            transformed['membership_status'] = extended_fields.get('members.membershipStatus')
            transformed['is_mobile_member'] = extended_fields.get('members.mobile')
        else:
            transformed['display_name_first_last'] = None
            transformed['display_name_last_first'] = None
            transformed['membership_status'] = None
            transformed['is_mobile_member'] = None

        return transformed

    @staticmethod
    def transform_contacts(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple contacts.

        Args:
            contacts: List of raw contact data from Wix API

        Returns:
            List of flattened contact data
        """
        transformed_contacts = []

        for contact in contacts:
            try:
                transformed = ContactsTransformer.transform_contact(contact)
                transformed_contacts.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming contact {contact.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Transformed {len(transformed_contacts)} contacts")
        return transformed_contacts

    @staticmethod
    def save_to_csv(contacts: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """
        Transform contacts and save directly to CSV.

        Args:
            contacts: List of raw contact data
            output_path: Path to output CSV file
            encoding: File encoding (default: 'utf-8-sig' for Excel compatibility)
            **kwargs: Additional arguments to pass to pandas.to_csv()
        """
        transformed = ContactsTransformer.transform_contacts(contacts)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
