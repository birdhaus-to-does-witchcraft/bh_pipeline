"""
Events data transformer.

Transforms raw Wix Events API data into clean, analysis-ready format.
Handles nested structures, date formatting, and data flattening.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class EventsTransformer(BaseTransformer):
    """Transform raw Wix events data into clean, flattened format."""

    @staticmethod
    def transform_event(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single event from raw API format to flattened format.

        Args:
            event: Raw event data from Wix API

        Returns:
            Flattened event data suitable for CSV export
        """
        transformed = {}

        # Basic fields
        transformed['event_id'] = event.get('id')
        transformed['title'] = event.get('title')
        transformed['slug'] = event.get('slug')
        transformed['status'] = event.get('status')
        transformed['short_description'] = event.get('shortDescription')

        # Categories - flatten to simple list of names
        categories = event.get('categories', {}).get('categories', [])
        if categories:
            transformed['category_names'] = ', '.join([cat.get('name', '') for cat in categories if cat.get('name')])
            transformed['category_count'] = len(categories)
            # Keep first category as primary
            transformed['primary_category'] = categories[0].get('name') if categories else None
        else:
            transformed['category_names'] = None
            transformed['category_count'] = 0
            transformed['primary_category'] = None

        # Date and time
        date_settings = event.get('dateAndTimeSettings', {})

        # Get timezone for proper time conversion (Wix API returns UTC times)
        timezone_id = date_settings.get('timeZoneId')

        # Extract date and time components using base class method
        # Pass timezone to convert from UTC to local time
        start_datetime = date_settings.get('startDate')
        end_datetime = date_settings.get('endDate')

        start_date, start_time = BaseTransformer.extract_date_and_time(start_datetime, timezone_id)
        end_date, end_time = BaseTransformer.extract_date_and_time(end_datetime, timezone_id)

        transformed['start_date'] = start_date
        transformed['start_time'] = start_time
        transformed['end_date'] = end_date
        transformed['end_time'] = end_time

        # Keep full datetime (UTC) if needed for reference
        transformed['start_datetime'] = start_datetime
        transformed['end_datetime'] = end_datetime

        transformed['timezone'] = timezone_id
        transformed['recurrence_status'] = date_settings.get('recurrenceStatus')

        # Day of week extraction (based on actual calendar date)
        if start_date:
            try:
                dt = datetime.strptime(start_date, '%Y-%m-%d')
                transformed['day_of_week'] = dt.strftime('%A')  # "Sunday", "Monday", etc.
                # Convert Python's weekday (0=Monday) to 0=Sunday format
                transformed['day_of_week_num'] = (dt.weekday() + 1) % 7  # 0=Sunday, 1=Monday, ..., 6=Saturday
                transformed['is_weekend'] = dt.weekday() in [5, 6]  # Saturday=5, Sunday=6 in Python's weekday()
            except (ValueError, TypeError):
                transformed['day_of_week'] = None
                transformed['day_of_week_num'] = None
                transformed['is_weekend'] = None
        else:
            transformed['day_of_week'] = None
            transformed['day_of_week_num'] = None
            transformed['is_weekend'] = None

        # Formatted date (human-readable)
        formatted = date_settings.get('formatted', {})
        transformed['formatted_date_time'] = formatted.get('dateAndTime')

        # Location
        location = event.get('location', {})
        transformed['location_name'] = location.get('name')
        transformed['location_type'] = location.get('type')

        address = location.get('address', {})
        transformed['location_address'] = address.get('formattedAddress')
        transformed['location_city'] = address.get('city')
        transformed['location_country'] = address.get('country')
        transformed['location_subdivision'] = address.get('subdivision')  # State/Province
        transformed['location_postal_code'] = address.get('postalCode')

        # Detailed street address breakdown
        street_address = address.get('streetAddress', {})
        transformed['street_number'] = street_address.get('number')
        transformed['street_name'] = street_address.get('name')
        transformed['street_apt'] = street_address.get('apt')

        geocode = address.get('geocode', {})
        transformed['location_latitude'] = geocode.get('latitude')
        transformed['location_longitude'] = geocode.get('longitude')

        # Registration
        registration = event.get('registration', {})
        transformed['registration_type'] = registration.get('type')  # TICKETING, RSVP, etc.
        transformed['registration_status'] = registration.get('status')

        # Ticket pricing
        tickets = registration.get('tickets', {})
        if tickets:
            transformed['currency'] = tickets.get('currency')

            lowest_price = tickets.get('lowestPrice', {})
            transformed['lowest_price'] = lowest_price.get('value') if lowest_price else None

            highest_price = tickets.get('highestPrice', {})
            transformed['highest_price'] = highest_price.get('value') if highest_price else None

            transformed['sold_out'] = tickets.get('soldOut', False)
        else:
            transformed['currency'] = None
            transformed['lowest_price'] = None
            transformed['highest_price'] = None
            transformed['sold_out'] = False

        # Images
        main_image = event.get('mainImage', {})
        transformed['main_image_url'] = main_image.get('url')
        transformed['main_image_id'] = main_image.get('id')
        transformed['main_image_width'] = main_image.get('width')
        transformed['main_image_height'] = main_image.get('height')

        # Metadata
        transformed['created_date'] = event.get('createdDate')
        transformed['updated_date'] = event.get('updatedDate')
        transformed['published_date'] = event.get('publishedDate')
        transformed['instance_id'] = event.get('instanceId')
        transformed['user_id'] = event.get('userId')

        # Guest list settings
        guest_settings = event.get('guestListSettings', {})
        transformed['guest_list_public'] = guest_settings.get('displayedPublicly', False)

        # Online conferencing
        online_conf = event.get('onlineConferencing', {})
        transformed['online_conference_enabled'] = online_conf.get('enabled', False)
        transformed['online_conference_type'] = online_conf.get('type')

        # Calendar URLs
        calendar_urls = event.get('calendarUrls', {})
        transformed['google_calendar_url'] = calendar_urls.get('google')
        transformed['ics_calendar_url'] = calendar_urls.get('ics')

        # Event page URL (merge base and path from API response)
        event_page_url = event.get('eventPageUrl', {})
        if event_page_url and isinstance(event_page_url, dict):
            base = event_page_url.get('base', '')
            path = event_page_url.get('path', '')
            transformed['event_page_url'] = f"{base}{path}" if base else None
        else:
            transformed['event_page_url'] = event_page_url

        # Description (multiple sources for complete coverage)
        # 1. Short description (already captured above as 'short_description')

        # 2. Detailed description (plain text field)
        transformed['detailed_description'] = event.get('detailedDescription', '')

        # 3. Rich text description (extract plain text from rich content nodes)
        description = event.get('description', {})
        if description and 'nodes' in description:
            # Extract plain text from rich text nodes
            transformed['description_rich_text'] = EventsTransformer._extract_text_from_nodes(
                description.get('nodes', [])
            )
        else:
            transformed['description_rich_text'] = None

        # 4. Combined description (use rich text if available, otherwise detailed)
        if transformed['description_rich_text']:
            transformed['description_full'] = transformed['description_rich_text']
        elif transformed['detailed_description']:
            transformed['description_full'] = transformed['detailed_description']
        else:
            transformed['description_full'] = transformed['short_description']

        return transformed

    @staticmethod
    def _extract_text_from_nodes(nodes: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from Wix rich text nodes.

        Args:
            nodes: List of rich text nodes

        Returns:
            Plain text content
        """
        text_parts = []

        for node in nodes:
            node_type = node.get('type')

            if node_type == 'TEXT':
                text_data = node.get('textData', {})
                text = text_data.get('text', '')
                if text:
                    text_parts.append(text)

            # Recursively process nested nodes
            if 'nodes' in node and node['nodes']:
                nested_text = EventsTransformer._extract_text_from_nodes(node['nodes'])
                if nested_text:
                    text_parts.append(nested_text)

        return ' '.join(text_parts).strip()

    @staticmethod
    def transform_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple events.

        Args:
            events: List of raw event data from Wix API

        Returns:
            List of flattened event data
        """
        transformed_events = []

        for event in events:
            try:
                transformed = EventsTransformer.transform_event(event)
                transformed_events.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming event {event.get('id', 'unknown')}: {e}")
                # Continue with other events
                continue

        logger.info(f"Transformed {len(transformed_events)} events")
        return transformed_events

    @staticmethod
    def save_to_csv(events: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """
        Transform events and save directly to CSV.

        Args:
            events: List of raw event data
            output_path: Path to output CSV file
            encoding: File encoding (default: 'utf-8-sig' for Excel compatibility)
                     - 'utf-8-sig': UTF-8 with BOM (Excel-friendly, recommended)
                     - 'utf-8': UTF-8 without BOM (standard)
                     - 'ascii': ASCII-only (replaces special chars)
            **kwargs: Additional arguments to pass to pandas.to_csv()
        """
        # Transform events first, then use base class save method
        transformed = EventsTransformer.transform_events(events)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
