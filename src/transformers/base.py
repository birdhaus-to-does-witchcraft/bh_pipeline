"""
Base transformer with shared utilities for all data types.

Provides common functionality for transforming raw API data into clean, CSV-ready format.
"""

import logging
from typing import Any, Dict, List
import pandas as pd

logger = logging.getLogger(__name__)


class BaseTransformer:
    """
    Base class for all data transformers.

    Provides shared functionality:
    - Character encoding/cleaning
    - DataFrame conversion
    - CSV export with proper encoding
    - Common data extraction methods
    """

    @staticmethod
    def clean_special_characters(df: pd.DataFrame) -> pd.DataFrame:
        """
        Replace special Unicode characters with ASCII equivalents.

        Args:
            df: pandas DataFrame

        Returns:
            Cleaned DataFrame with ASCII characters
        """
        # Mapping of special characters to ASCII equivalents
        char_replacements = {
            '\u2013': '-',      # EN DASH → hyphen
            '\u2014': '-',      # EM DASH → hyphen
            '\u2018': "'",      # LEFT SINGLE QUOTATION MARK → apostrophe
            '\u2019': "'",      # RIGHT SINGLE QUOTATION MARK → apostrophe
            '\u201C': '"',      # LEFT DOUBLE QUOTATION MARK → quote
            '\u201D': '"',      # RIGHT DOUBLE QUOTATION MARK → quote
            '\u2026': '...',    # HORIZONTAL ELLIPSIS → three periods
            '\u00A0': ' ',      # NO-BREAK SPACE → regular space
            '\u00E9': 'e',      # é → e
            '\u00E8': 'e',      # è → e
            '\u00E0': 'a',      # à → a
        }

        # Apply to all string columns
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                for old_char, new_char in char_replacements.items():
                    df[col] = df[col].str.replace(old_char, new_char, regex=False)

        return df

    @staticmethod
    def extract_date_and_time(datetime_str: str) -> tuple:
        """
        Extract date and time components from ISO datetime string.

        Args:
            datetime_str: ISO datetime string (e.g., "2025-10-12T16:00:00Z")

        Returns:
            Tuple of (date, time) strings, or (None, None) if invalid
        """
        if not datetime_str or 'T' not in datetime_str:
            return (datetime_str, None)

        try:
            date_part, time_part = datetime_str.split('T')
            # Remove 'Z' timezone indicator
            time_part = time_part.replace('Z', '')
            return (date_part, time_part)
        except Exception:
            return (datetime_str, None)

    @staticmethod
    def flatten_price(price_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten price object into simple fields.

        Args:
            price_obj: Price object with value, currency, formattedValue

        Returns:
            Dict with flattened price fields
        """
        if not price_obj:
            return {'value': None, 'currency': None, 'formatted': None}

        return {
            'value': price_obj.get('value'),
            'currency': price_obj.get('currency'),
            'formatted': price_obj.get('formattedValue')
        }

    @staticmethod
    def to_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert list of dictionaries to pandas DataFrame.

        Args:
            data: List of transformed data dictionaries

        Returns:
            pandas DataFrame

        Raises:
            ImportError: If pandas is not installed
        """
        try:
            return pd.DataFrame(data)
        except ImportError:
            logger.error("pandas is required for DataFrame conversion")
            raise

    @staticmethod
    def save_to_csv(
        data: List[Dict[str, Any]],
        output_path: str,
        encoding: str = 'utf-8-sig',
        **kwargs
    ):
        """
        Save transformed data to CSV file.

        Args:
            data: List of transformed data dictionaries
            output_path: Path to output CSV file
            encoding: File encoding (default: 'utf-8-sig' for Excel compatibility)
                     - 'utf-8-sig': UTF-8 with BOM (Excel-friendly, recommended)
                     - 'utf-8': UTF-8 without BOM (standard)
                     - 'ascii': ASCII-only (replaces special chars)
            **kwargs: Additional arguments to pass to pandas.to_csv()
        """
        df = BaseTransformer.to_dataframe(data)

        # Replace special characters if ASCII encoding requested
        if encoding == 'ascii':
            df = BaseTransformer.clean_special_characters(df)
            encoding = 'ascii'

        # Default CSV options
        csv_options = {
            'index': False,
            'encoding': encoding,
            'date_format': '%Y-%m-%d %H:%M:%S'
        }
        csv_options.update(kwargs)

        df.to_csv(output_path, **csv_options)
        logger.info(f"Saved {len(df)} records to {output_path} (encoding: {encoding})")

    @staticmethod
    def extract_address_components(address: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and flatten address components.

        Args:
            address: Address object from API

        Returns:
            Dict with flattened address fields
        """
        if not address:
            return {
                'formatted_address': None,
                'city': None,
                'country': None,
                'subdivision': None,
                'postal_code': None,
                'street_number': None,
                'street_name': None,
                'street_apt': None,
                'latitude': None,
                'longitude': None
            }

        street_address = address.get('streetAddress', {})
        geocode = address.get('geocode', {})

        return {
            'formatted_address': address.get('formattedAddress'),
            'city': address.get('city'),
            'country': address.get('country'),
            'subdivision': address.get('subdivision'),
            'postal_code': address.get('postalCode'),
            'street_number': street_address.get('number'),
            'street_name': street_address.get('name'),
            'street_apt': street_address.get('apt'),
            'latitude': geocode.get('latitude'),
            'longitude': geocode.get('longitude')
        }
