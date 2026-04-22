"""
Wix Form Submissions API V4 wrapper.

Provides high-level methods for querying form submissions across namespaces.

NOTE on endpoint URL:
Wix's docs are inconsistent for this API. The schema lists
`https://www.wixapis.com/v4/submissions/namespace/query` (returns 404), but
the cURL examples (and what actually works) use
`https://www.wixapis.com/form-submission/v4/submissions/namespace/query`.

Base URL: https://www.wixapis.com
Documentation: https://dev.wix.com/docs/rest/crm/forms/form-submissions/query-submissions-by-namespace
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_cursor_query

logger = logging.getLogger(__name__)

# Known namespaces that contain form submissions.
# wix.form_app.form  -- standalone Wix Forms (contact, signup, custom)
# wix.events_app.form -- event registration forms
# wix.bookings_app.form -- booking intake forms
KNOWN_NAMESPACES = [
    "wix.form_app.form",
    "wix.events_app.form",
    "wix.bookings_app.form",
]


class FormsAPI:
    """
    Wrapper for Wix Form Submissions API V4.

    Uses cursor-based pagination. Each query MUST include a namespace filter.

    Example:
        >>> client = WixAPIClient.from_env()
        >>> forms_api = FormsAPI(client)
        >>> submissions = forms_api.get_all_submissions("wix.form_app.form")
    """

    def __init__(self, client: WixAPIClient):
        self.client = client
        # Note the /form-submission prefix - schema says /v4/submissions/...
        # but that 404s. cURL examples use the prefixed path.
        self.base_path = "/form-submission/v4/submissions/namespace/query"

    def query_submissions(
        self,
        namespace: str,
        form_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Query form submissions by namespace.

        Endpoint: POST /v4/submissions/namespace/query

        Args:
            namespace: Required namespace filter (e.g. "wix.form_app.form")
            form_id: Optional form ID to filter by
            cursor: Cursor token for pagination (None for first page)
            limit: Number of items per page (max 100)

        Returns:
            Response with submissions list and pagingMetadata
        """
        filter_obj: Dict[str, Any] = {"namespace": namespace}
        if form_id:
            filter_obj["formId"] = form_id

        query: Dict[str, Any] = {
            "filter": filter_obj,
            "cursorPaging": {"limit": limit},
        }
        if cursor:
            query["cursorPaging"]["cursor"] = cursor

        payload = {"query": query}

        logger.info(
            f"Querying submissions (namespace={namespace}, form_id={form_id}, limit={limit})"
        )
        return self.client.post(self.base_path, json=payload)

    def get_all_submissions(
        self,
        namespace: str,
        form_id: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all submissions for a namespace using cursor pagination.

        Args:
            namespace: Namespace to query
            form_id: Optional form ID filter
            max_results: Maximum results to return (None = all)

        Returns:
            List of all matching submissions
        """
        def query_func(cursor: Optional[str], limit: int, **kwargs) -> Dict[str, Any]:
            return self.query_submissions(
                namespace=namespace,
                form_id=form_id,
                cursor=cursor,
                limit=limit,
            )

        return paginate_cursor_query(
            query_func=query_func,
            response_key="submissions",
            limit=100,
            max_results=max_results,
        )

    def get_all_submissions_for_namespaces(
        self,
        namespaces: Optional[List[str]] = None,
        max_results_per_namespace: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve submissions across multiple namespaces.

        Args:
            namespaces: List of namespaces to query (default: KNOWN_NAMESPACES)
            max_results_per_namespace: Max results per namespace (None = all)

        Returns:
            Combined list of submissions from all namespaces
        """
        if namespaces is None:
            namespaces = KNOWN_NAMESPACES

        all_submissions = []

        for ns in namespaces:
            logger.info(f"Fetching submissions for namespace: {ns}")
            try:
                submissions = self.get_all_submissions(
                    namespace=ns,
                    max_results=max_results_per_namespace,
                )
                logger.info(f"Retrieved {len(submissions)} submissions from {ns}")
                all_submissions.extend(submissions)
            except Exception as e:
                logger.warning(f"Could not fetch submissions for namespace {ns}: {e}")

        logger.info(f"Total submissions across all namespaces: {len(all_submissions)}")
        return all_submissions
