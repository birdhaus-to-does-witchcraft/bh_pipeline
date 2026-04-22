"""
Automations data transformer.

Transforms raw Wix Automations API data into clean, analysis-ready format.
"""

import logging
from typing import Any, Dict, List

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


class AutomationsTransformer(BaseTransformer):
    """Transform raw Wix automation config data into clean, flattened format."""

    @staticmethod
    def transform_automation(automation: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single automation record."""
        transformed = {}

        transformed['automation_id'] = automation.get('id')
        transformed['name'] = automation.get('name')
        transformed['description'] = automation.get('description')
        transformed['status'] = automation.get('status')
        transformed['origin'] = automation.get('origin')

        # Application info
        app_info = automation.get('applicationInfo', {})
        transformed['app_id'] = app_info.get('appDefId')

        # Configuration
        config = automation.get('configuration', {})

        # Trigger
        trigger = config.get('trigger', {})
        transformed['trigger_key'] = trigger.get('triggerKey')
        transformed['trigger_app_id'] = trigger.get('appId')

        # Actions (flatten first action, count total)
        actions = config.get('actions', [])
        transformed['action_count'] = len(actions)

        if actions:
            first_action = actions[0]
            transformed['first_action_key'] = first_action.get('actionKey')
            transformed['first_action_app_id'] = first_action.get('appId')

            # Summarize all action keys
            action_keys = [a.get('actionKey', '') for a in actions]
            transformed['all_action_keys'] = '; '.join(filter(None, action_keys))
        else:
            transformed['first_action_key'] = None
            transformed['first_action_app_id'] = None
            transformed['all_action_keys'] = None

        # Dates
        created = automation.get('createdDate') or automation.get('_createdDate')
        updated = automation.get('updatedDate') or automation.get('_updatedDate')

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
    def transform_automations(automations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple automation records."""
        transformed_automations = []
        for automation in automations:
            try:
                transformed_automations.append(
                    AutomationsTransformer.transform_automation(automation)
                )
            except Exception as e:
                logger.error(f"Error transforming automation {automation.get('id', 'unknown')}: {e}")
        logger.info(f"Transformed {len(transformed_automations)} automations")
        return transformed_automations

    @staticmethod
    def save_to_csv(automations: List[Dict[str, Any]], output_path: str, encoding: str = 'utf-8-sig', **kwargs):
        """Transform automations and save to CSV."""
        transformed = AutomationsTransformer.transform_automations(automations)
        BaseTransformer.save_to_csv(transformed, output_path, encoding=encoding, **kwargs)
