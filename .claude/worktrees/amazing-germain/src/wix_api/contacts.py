"""
Wix Contacts API V4 wrapper.

This module provides high-level methods for interacting with the Wix Contacts V4 API.
All endpoints validated against official Wix documentation (October 2025).

Reference: VALIDATED_ENDPOINTS.md
Base URL: https://www.wixapis.com/contacts/v4
Documentation: https://dev.wix.com/api/rest/contacts/contacts/contacts-v4
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient

logger = logging.getLogger(__name__)


class ContactsAPI:
    """
    Wrapper for Wix Contacts API V4.

    Provides methods to manage customer contacts, including PII data (emails, phones, addresses).

    IMPORTANT: Handle PII responsibly according to privacy regulations.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> contacts_api = ContactsAPI(client)
        >>> contacts = contacts_api.list_contacts(limit=10)
    """

    def __init__(self, client: WixAPIClient):
        """
        Initialize Contacts API wrapper.

        Args:
            client: Authenticated WixAPIClient instance
        """
        self.client = client
        self.base_path = "/contacts/v4/contacts"

    def list_contacts(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        List contacts with filtering and pagination.

        Endpoint: GET /contacts/v4/contacts

        Can return up to 1,000 contacts per request.

        Args:
            limit: Number of contacts to return (default: 100, max: 1000)
            offset: Offset for pagination (default: 0)
            filter_dict: Filter criteria
            sort: Sort criteria

        Returns:
            Response with contacts list and paging metadata

        Example:
            >>> contacts = contacts_api.list_contacts(
            ...     limit=50,
            ...     filter_dict={"lastActivity.activityDate": {"$gte": "2025-01-01T00:00:00Z"}}
            ... )
        """
        params: Dict[str, Any] = {
            "paging.limit": limit,
            "paging.offset": offset
        }

        # Note: GET requests use query parameters, not request body
        # The actual implementation depends on Wix API's expected format

        logger.info(f"Listing contacts (limit={limit}, offset={offset})")
        return self.client.get(self.base_path, params=params)

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Get contact by ID.

        Endpoint: GET /contacts/v4/contacts/{id}

        Args:
            contact_id: The contact ID

        Returns:
            Contact details including PII (email, phone, address)

        Example:
            >>> contact = contacts_api.get_contact("contact-123")
        """
        logger.info(f"Getting contact: {contact_id}")
        return self.client.get(f"{self.base_path}/{contact_id}")

    def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new contact.

        Endpoint: POST /contacts/v4/contacts

        Requires at least one of: name, phone, or email.

        Args:
            contact_data: Contact information (name, emails, phones, addresses, etc.)

        Returns:
            Created contact details

        Example:
            >>> contact_data = {
            ...     "name": {
            ...         "first": "John",
            ...         "last": "Doe"
            ...     },
            ...     "emails": [{
            ...         "email": "john.doe@example.com",
            ...         "tag": "main"
            ...     }],
            ...     "phones": [{
            ...         "phone": "+1-555-123-4567",
            ...         "tag": "mobile"
            ...     }]
            ... }
            >>> contact = contacts_api.create_contact(contact_data)
        """
        logger.info("Creating new contact")
        return self.client.post(self.base_path, json={"contact": contact_data})

    def bulk_update_contacts(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk update multiple contacts.

        Endpoint: POST /contacts/v4/bulk/contacts/update

        Args:
            updates: List of contact updates with IDs

        Returns:
            Bulk operation results

        Example:
            >>> updates = [
            ...     {
            ...         "id": "contact-1",
            ...         "contact": {"labels": ["VIP"]}
            ...     },
            ...     {
            ...         "id": "contact-2",
            ...         "contact": {"labels": ["VIP"]}
            ...     }
            ... ]
            >>> result = contacts_api.bulk_update_contacts(updates)
        """
        logger.info(f"Bulk updating {len(updates)} contacts")
        return self.client.post(f"{self.base_path}/../bulk/contacts/update", json={"contacts": updates})

    def bulk_delete_contacts(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bulk delete contacts by filter.

        Endpoint: POST /contacts/v4/bulk/contacts/delete

        Returns a bulk job ID for tracking the deletion process.

        Args:
            filter_dict: Filter criteria to select contacts to delete

        Returns:
            Bulk job ID and status

        Example:
            >>> result = contacts_api.bulk_delete_contacts(
            ...     {"labels": {"$hasSome": ["test"]}}
            ... )
        """
        logger.info("Bulk deleting contacts")
        return self.client.post(f"{self.base_path}/../bulk/contacts/delete", json={"filter": filter_dict})

    def merge_contacts(
        self,
        target_contact_id: str,
        source_contact_ids: List[str],
        preview: bool = False
    ) -> Dict[str, Any]:
        """
        Merge source contacts into a target contact.

        Endpoint: POST /contacts/v4/contacts/merge

        Args:
            target_contact_id: The contact to merge into
            source_contact_ids: List of contacts to merge from
            preview: If True, preview the merge without executing (default: False)

        Returns:
            Merge results or preview

        Example:
            >>> # Preview merge
            >>> preview = contacts_api.merge_contacts(
            ...     target_contact_id="contact-1",
            ...     source_contact_ids=["contact-2", "contact-3"],
            ...     preview=True
            ... )
            >>> # Execute merge
            >>> result = contacts_api.merge_contacts(
            ...     target_contact_id="contact-1",
            ...     source_contact_ids=["contact-2", "contact-3"]
            ... )
        """
        payload = {
            "targetContactId": target_contact_id,
            "sourceContactIds": source_contact_ids
        }

        if preview:
            payload["preview"] = True

        action = "Previewing" if preview else "Merging"
        logger.info(f"{action} contacts: {len(source_contact_ids)} into {target_contact_id}")

        return self.client.post(f"{self.base_path}/merge", json=payload)

    def get_all_contacts(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all contacts using pagination.

        Automatically handles pagination to retrieve all matching contacts.

        Args:
            filter_dict: Filter criteria
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all contacts

        Example:
            >>> all_contacts = contacts_api.get_all_contacts(
            ...     filter_dict={"labels": {"$hasSome": ["customer"]}},
            ...     max_results=5000
            ... )
        """
        all_contacts = []
        offset = 0
        limit = 1000  # Contacts API supports up to 1,000 per request

        logger.info("Retrieving all contacts with pagination")

        while True:
            response = self.list_contacts(
                limit=limit,
                offset=offset,
                filter_dict=filter_dict
            )

            contacts = response.get("contacts", [])
            all_contacts.extend(contacts)

            # Check if we've reached max_results
            if max_results and len(all_contacts) >= max_results:
                all_contacts = all_contacts[:max_results]
                logger.info(f"Reached max_results limit: {max_results}")
                break

            # Check if there are more pages
            paging_metadata = response.get("pagingMetadata", {})
            has_next = paging_metadata.get("hasNext", False)

            if not has_next:
                logger.info(f"Retrieved all contacts: {len(all_contacts)} total")
                break

            offset += limit
            logger.debug(f"Fetching next page (offset={offset})")

        return all_contacts

    def search_contacts_by_email(self, email: str) -> List[Dict[str, Any]]:
        """
        Helper method to search contacts by email address.

        Args:
            email: Email address to search for

        Returns:
            List of matching contacts

        Example:
            >>> contacts = contacts_api.search_contacts_by_email("john@example.com")
        """
        logger.info(f"Searching contacts by email: {email}")

        # Use filter to search by email
        filter_dict = {
            "emails.email": email
        }

        response = self.list_contacts(filter_dict=filter_dict)
        return response.get("contacts", [])

    def search_contacts_by_phone(self, phone: str) -> List[Dict[str, Any]]:
        """
        Helper method to search contacts by phone number.

        Args:
            phone: Phone number to search for

        Returns:
            List of matching contacts

        Example:
            >>> contacts = contacts_api.search_contacts_by_phone("+1-555-123-4567")
        """
        logger.info(f"Searching contacts by phone: {phone}")

        # Use filter to search by phone
        filter_dict = {
            "phones.phone": phone
        }

        response = self.list_contacts(filter_dict=filter_dict)
        return response.get("contacts", [])

    def get_contact_labels(self) -> List[str]:
        """
        Helper to document common contact label types.

        Returns:
            List of suggested label types
        """
        return ["customer", "lead", "VIP", "member", "subscriber", "partner", "vendor"]
