"""
Wix Members API V1 wrapper.

Provides high-level methods for interacting with the Wix Members V1 API.

Base URL: https://www.wixapis.com/members/v1
Documentation: https://dev.wix.com/docs/rest/crm/members-contacts/members/members/list-members
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_query

logger = logging.getLogger(__name__)


class MembersAPI:
    """
    Wrapper for Wix Members API V1.

    Provides methods to list and retrieve site members (users with logins).
    Members are a subset of Contacts -- every Member has a Contact, but not
    every Contact is a Member.

    Example:
        >>> client = WixAPIClient.from_env()
        >>> members_api = MembersAPI(client)
        >>> members = members_api.get_all_members()
    """

    def __init__(self, client: WixAPIClient):
        self.client = client
        self.base_path = "/members/v1/members"

    def list_members(
        self,
        limit: int = 100,
        offset: int = 0,
        fieldsets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        List site members with pagination.

        Endpoint: GET /members/v1/members

        Args:
            limit: Number of members to return (default: 100)
            offset: Offset for pagination (default: 0)
            fieldsets: Predefined field sets (PUBLIC, EXTENDED, FULL).
                       Default FULL for admin access.

        Returns:
            Response with members list and total count
        """
        params: Dict[str, Any] = {
            "paging.limit": limit,
            "paging.offset": offset,
        }

        if fieldsets:
            for fs in fieldsets:
                params.setdefault("fieldsets", []).append(fs)
        else:
            params["fieldsets"] = "FULL"

        logger.info(f"Listing members (limit={limit}, offset={offset})")
        return self.client.get(self.base_path, params=params)

    def get_member(self, member_id: str) -> Dict[str, Any]:
        """
        Get member by ID.

        Endpoint: GET /members/v1/members/{memberId}
        """
        logger.info(f"Getting member: {member_id}")
        return self.client.get(f"{self.base_path}/{member_id}")

    def get_all_members(
        self,
        fieldsets: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all site members using pagination.

        Args:
            fieldsets: Predefined field sets (default: FULL)
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all members
        """
        def query_func(limit: int, offset: int, **kwargs) -> Dict[str, Any]:
            return self.list_members(
                limit=limit,
                offset=offset,
                fieldsets=kwargs.get("fieldsets"),
            )

        return paginate_query(
            query_func=query_func,
            response_key="members",
            limit=100,
            max_results=max_results,
            fieldsets=fieldsets,
        )
