import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.profile import RuleProfile

logger = logging.getLogger(__name__)

DEFAULT_PRESET_PATH = (
    Path(__file__).resolve().parents[2]
    / "resources"
    / "rule_presets"
    / "department_vkr_2025.yaml"
)


class ProfileService:
    """Service for resolving and retrieving rule profiles and presets."""

    @staticmethod
    def load_yaml_preset(preset_path: Optional[Path | str] = None) -> dict[str, Any]:
        """
        Loads and parses a YAML preset file, returning the 'rules' dictionary section.

        Args:
            preset_path: Optional path to the YAML preset file.

        Returns:
            dict containing rule settings.
        """
        path = Path(preset_path) if preset_path else DEFAULT_PRESET_PATH
        if not path.is_file():
            logger.warning("Preset YAML file not found: %s", path)
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            rules = data.get("rules", {})
            if isinstance(rules, dict):
                return rules
            logger.warning("'rules' key in preset is not a dictionary: %s", path)
            return {}
        except Exception:
            logger.exception("Failed to load and parse YAML preset from %s", path)
            return {}

    @classmethod
    async def get_active_profile_config(
        cls,
        session: Optional[AsyncSession] = None,
        profile_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Get active profile configuration rules.

        - If profile_id is provided and RuleProfile is found in DB, returns its rules_config.
        - Otherwise, loads and parses the default YAML file
          resources/rule_presets/department_vkr_2025.yaml and returns the 'rules' section.

        Args:
            session: Optional async SQLAlchemy session.
            profile_id: Optional ID of the rule profile.

        Returns:
            dict[str, Any]: Rules configuration mapping rule_id to rule parameters.
        """
        if session is not None and profile_id is not None:
            try:
                query = select(RuleProfile).where(RuleProfile.id == profile_id)
                result = await session.execute(query)
                profile = result.scalar_one_or_none()
                if profile is not None and isinstance(profile.rules_config, dict):
                    return profile.rules_config
            except Exception:
                logger.exception(
                    "Error querying RuleProfile with id %s, falling back to default YAML preset",
                    profile_id,
                )

        return cls.load_yaml_preset()
