"""
Members data transformer.

Transforms raw Wix Members API data into clean, analysis-ready format.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class MembersTransformer(BaseTransformer):
    """Transform raw Wix member data into clean, flattened format."""

    @staticmethod
    def transform_member(member: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single member record."""
        transformed = {}

        transformed['member_id'] = member.get('id')
        transformed['login_email'] = member.get('loginEmail')
        transformed['status'] = member.get('status')
        transformed['privacy_status'] = member.get('privacyStatus')
        transformed['activity_status'] = member.get('activityStatus')

        # Profile
        profile = member.get('profile', {})
        transformed['nickname'] = profile.get('nickname')
        transformed['slug'] = profile.get('slug')
        transformed['profile_photo_url'] = profile.get('photo', {}).get('url')
        transformed['cover_photo_url'] = profile.get('cover', {}).get('url')
        transformed['title'] = profile.get('title')

        # Contact info from profile
        transformed['first_name'] = profile.get('firstName')
        transformed['last_name'] = profile.get('lastName')

        # Contact ID link
        transformed['contact_id'] = member.get('contactId')

        # Dates
        created = member.get('createdDate')
        updated = member.get('updatedDate')

        if created:
            created_date, created_time = BaseTransformer.extract_date_and_time(created)
            transformed['created_date'] = created_date
            transformed['created_time'] = created_time
        else:
            transformed['created_date'] = None
            transformed['created_time'] = None

        if updated:
            updated_date, updated_time = BaseTransformer.extract_date_and_time(updated)
            transformed['updated_date'] = updated_date
            transformed['updated_time'] = updated_time
        else:
            transformed['updated_date'] = None
            transformed['updated_time'] = None

        last_login = member.get('lastLoginDate')
        if last_login:
            login_date, login_time = BaseTransformer.extract_date_and_time(last_login)
            transformed['last_login_date'] = login_date
            transformed['last_login_time'] = login_time
        else:
            transformed['last_login_date'] = None
            transformed['last_login_time'] = None

        return transformed

    @staticmethod
    def transform_members(members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple member records."""
        transformed_members = []
        for member in members:
            try:
                transformed_members.append(MembersTransformer.transform_member(member))
            except Exception as e:
                logger.error(f"Error transforming member {member.get('id', 'unknown')}: {e}")
        logger.info(f"Transformed {len(transformed_members)} members")
        return transformed_members

    @staticmethod
    def save_to_csv(members: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """Transform members and save to CSV."""
        transformed = MembersTransformer.transform_members(members)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
