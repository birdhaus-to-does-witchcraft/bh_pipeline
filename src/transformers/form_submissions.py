"""
Form submissions data transformer.

Transforms raw Wix Form Submissions API data into clean, analysis-ready format.
Handles dynamic submission fields that vary per form.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class FormSubmissionsTransformer(BaseTransformer):
    """Transform raw Wix form submission data into clean, flattened format."""

    @staticmethod
    def transform_submission(submission: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single form submission record."""
        transformed = {}

        transformed['submission_id'] = submission.get('id') or submission.get('_id')
        transformed['form_id'] = submission.get('formId')
        transformed['namespace'] = submission.get('namespace')
        transformed['status'] = submission.get('status')

        # Submitter
        submitter = submission.get('submitter', {})
        transformed['submitter_contact_id'] = submitter.get('contactId')
        transformed['submitter_member_id'] = submitter.get('memberId')

        # Dates
        created = submission.get('createdDate') or submission.get('_createdDate')
        updated = submission.get('updatedDate') or submission.get('_updatedDate')

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

        transformed['seen'] = submission.get('seen')

        # Dynamic submission fields - flatten all key/value pairs
        submissions_data = submission.get('submissions', {})
        for field_key, field_value in submissions_data.items():
            safe_key = f"field_{field_key.replace(' ', '_').replace('.', '_').lower()}"
            if isinstance(field_value, dict):
                transformed[safe_key] = str(field_value)
            elif isinstance(field_value, list):
                transformed[safe_key] = '; '.join(str(v) for v in field_value)
            else:
                transformed[safe_key] = field_value

        return transformed

    @staticmethod
    def transform_submissions(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple form submission records."""
        transformed_submissions = []
        for submission in submissions:
            try:
                transformed_submissions.append(
                    FormSubmissionsTransformer.transform_submission(submission)
                )
            except Exception as e:
                sid = submission.get('id') or submission.get('_id', 'unknown')
                logger.error(f"Error transforming submission {sid}: {e}")
        logger.info(f"Transformed {len(transformed_submissions)} form submissions")
        return transformed_submissions

    @staticmethod
    def save_to_csv(submissions: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """Transform form submissions and save to wide-format CSV."""
        transformed = FormSubmissionsTransformer.transform_submissions(submissions)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)

    @staticmethod
    def transform_submission_long(submission: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform a single submission into long-format rows (one row per field).

        Long format has a stable schema regardless of which forms exist:
            submission_id, form_id, namespace, submitter_contact_id,
            submitter_member_id, status, created_date, field_name, field_value
        """
        submitter = submission.get('submitter', {})
        created = submission.get('createdDate') or submission.get('_createdDate')

        if created:
            created_date, _created_time = BaseTransformer.extract_date_and_time(created)
        else:
            created_date = None

        base = {
            'submission_id': submission.get('id') or submission.get('_id'),
            'form_id': submission.get('formId'),
            'namespace': submission.get('namespace'),
            'submitter_contact_id': submitter.get('contactId'),
            'submitter_member_id': submitter.get('memberId'),
            'status': submission.get('status'),
            'created_date': created_date,
        }

        rows: List[Dict[str, Any]] = []
        submissions_data = submission.get('submissions', {}) or {}

        if not submissions_data:
            # Emit one empty row so the submission is still represented
            rows.append({**base, 'field_name': None, 'field_value': None})
            return rows

        for field_key, field_value in submissions_data.items():
            if isinstance(field_value, dict):
                value_str = str(field_value)
            elif isinstance(field_value, list):
                value_str = '; '.join(str(v) for v in field_value)
            else:
                value_str = field_value if field_value is None else str(field_value)
            rows.append({**base, 'field_name': field_key, 'field_value': value_str})

        return rows

    @staticmethod
    def transform_submissions_long(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple submissions into long-format rows."""
        all_rows: List[Dict[str, Any]] = []
        for submission in submissions:
            try:
                all_rows.extend(
                    FormSubmissionsTransformer.transform_submission_long(submission)
                )
            except Exception as e:
                sid = submission.get('id') or submission.get('_id', 'unknown')
                logger.error(f"Error long-transforming submission {sid}: {e}")
        logger.info(
            f"Generated {len(all_rows)} long-format rows from {len(submissions)} submissions"
        )
        return all_rows

    @staticmethod
    def save_to_csv_long(
        submissions: List[Dict[str, Any]],
        output_path: str,
        encoding: str = 'utf-8-sig',
        **kwargs,
    ):
        """Transform submissions to long format and save to CSV."""
        rows = FormSubmissionsTransformer.transform_submissions_long(submissions)
        BaseTransformer.save_to_csv(rows, output_path, encoding=encoding, **kwargs)
