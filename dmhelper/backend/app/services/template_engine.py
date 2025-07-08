"""Template engine for loading and processing D&D 5e character templates."""

import logging
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from app.core.config import get_settings
from app.services.character_service import (
    Character, AbilityScores, EquipmentItem, CharacterFeature,
    CharacterService, AbilityScoreMethod
)

logger = logging.getLogger(__name__)


@dataclass
class CharacterTemplate:
    """Character template loaded from YAML."""
    
    # Template metadata
    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0"
    
    # Character basics
    race: str = ""
    character_class: str = ""
    background: str = ""
    level: int = 1
    
    # Ability scores (base values before racial bonuses)
    ability_scores: Dict[str, int] = field(default_factory=dict)
    
    # Proficiencies
    skill_proficiencies: List[str] = field(default_factory=list)
    saving_throw_proficiencies: List[str] = field(default_factory=list)
    armor_proficiencies: List[str] = field(default_factory=list)
    weapon_proficiencies: List[str] = field(default_factory=list)
    tool_proficiencies: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    
    # Equipment
    equipment: List[Dict[str, Any]] = field(default_factory=list)
    
    # Features
    features: List[Dict[str, Any]] = field(default_factory=list)
    
    # Optional overrides
    hit_points: Optional[int] = None
    armor_class: Optional[int] = None
    speed: Optional[int] = None
    
    # Template options
    customizable_fields: List[str] = field(default_factory=list)
    required_choices: Dict[str, List[str]] = field(default_factory=dict)
    
    # File metadata
    file_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "race": self.race,
            "character_class": self.character_class,
            "background": self.background,
            "level": self.level,
            "ability_scores": self.ability_scores,
            "skill_proficiencies": self.skill_proficiencies,
            "saving_throw_proficiencies": self.saving_throw_proficiencies,
            "armor_proficiencies": self.armor_proficiencies,
            "weapon_proficiencies": self.weapon_proficiencies,
            "tool_proficiencies": self.tool_proficiencies,
            "languages": self.languages,
            "equipment": self.equipment,
            "features": self.features,
            "hit_points": self.hit_points,
            "armor_class": self.armor_class,
            "speed": self.speed,
            "customizable_fields": self.customizable_fields,
            "required_choices": self.required_choices
        }


class TemplateValidationError(Exception):
    """Raised when a template fails validation."""
    pass


class TemplateEngine:
    """Engine for loading, validating, and processing character templates."""
    
    def __init__(self, character_service: Optional[CharacterService] = None):
        self.settings = get_settings()
        self.templates_dir = Path(self.settings.campaign_root) / "characters" / "templates"
        self.character_service = character_service or CharacterService()
        
        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Template cache
        self._template_cache: Dict[str, CharacterTemplate] = {}
        self._last_scan_time = 0.0
    
    def scan_templates(self, force_refresh: bool = False) -> None:
        """Scan the templates directory for YAML files."""
        import time
        current_time = time.time()
        
        # Only scan if forced or enough time has passed
        if not force_refresh and (current_time - self._last_scan_time) < 60:
            return
        
        self._template_cache.clear()
        
        try:
            for yaml_file in self.templates_dir.glob("*.yaml"):
                try:
                    template = self.load_template_from_file(yaml_file)
                    if template:
                        template_id = yaml_file.stem
                        self._template_cache[template_id] = template
                        logger.debug(f"Loaded template: {template.name} from {yaml_file}")
                except Exception as e:
                    logger.error(f"Failed to load template from {yaml_file}: {e}")
            
            # Also scan .yml files
            for yaml_file in self.templates_dir.glob("*.yml"):
                try:
                    template = self.load_template_from_file(yaml_file)
                    if template:
                        template_id = yaml_file.stem
                        self._template_cache[template_id] = template
                        logger.debug(f"Loaded template: {template.name} from {yaml_file}")
                except Exception as e:
                    logger.error(f"Failed to load template from {yaml_file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to scan templates directory: {e}")
        
        self._last_scan_time = current_time
        logger.info(f"Scanned templates directory, found {len(self._template_cache)} templates")
    
    def load_template_from_file(self, file_path: Path) -> Optional[CharacterTemplate]:
        """Load a single template from a YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Empty template file: {file_path}")
                return None
            
            template = self._dict_to_template(data)
            template.file_path = str(file_path)
            
            # Validate the template
            self.validate_template(template)
            
            return template
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading template from {file_path}: {e}")
            return None
    
    def _dict_to_template(self, data: Dict[str, Any]) -> CharacterTemplate:
        """Convert dictionary data to CharacterTemplate."""
        
        # Handle proficiencies (may be nested in YAML)
        proficiencies = data.get("proficiencies", {})
        
        return CharacterTemplate(
            name=data.get("name", "Unnamed Template"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
            race=data.get("race", ""),
            character_class=data.get("character_class", data.get("class", "")),
            background=data.get("background", ""),
            level=data.get("level", 1),
            ability_scores=data.get("ability_scores", {}),
            skill_proficiencies=self._extract_proficiency_list(proficiencies, "skills"),
            saving_throw_proficiencies=self._extract_proficiency_list(proficiencies, "saving_throws"),
            armor_proficiencies=self._extract_proficiency_list(proficiencies, "armor"),
            weapon_proficiencies=self._extract_proficiency_list(proficiencies, "weapons"),
            tool_proficiencies=self._extract_proficiency_list(proficiencies, "tools"),
            languages=data.get("languages", []),
            equipment=data.get("equipment", []),
            features=data.get("features", []),
            hit_points=data.get("hit_points"),
            armor_class=data.get("armor_class"),
            speed=data.get("speed"),
            customizable_fields=data.get("customizable_fields", []),
            required_choices=data.get("required_choices", {})
        )
    
    def _extract_proficiency_list(self, proficiencies: Dict[str, Any], key: str) -> List[str]:
        """Extract a proficiency list from nested proficiencies dict."""
        value = proficiencies.get(key, [])
        
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            return [value]
        else:
            return []
    
    def validate_template(self, template: CharacterTemplate) -> None:
        """Validate a template against D&D 5e rules."""
        errors = []
        
        # Check required fields
        if not template.name:
            errors.append("Template must have a name")
        
        # Validate ability scores if provided
        if template.ability_scores:
            for ability, score in template.ability_scores.items():
                if ability not in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                    errors.append(f"Unknown ability score: {ability}")
                elif not isinstance(score, int) or score < 1 or score > 30:
                    errors.append(f"Invalid {ability} score: {score} (must be 1-30)")
        
        # Validate level
        if template.level < 1 or template.level > 20:
            errors.append(f"Invalid level: {template.level} (must be 1-20)")
        
        # Validate hit points if provided
        if template.hit_points is not None and template.hit_points < 1:
            errors.append("Hit points must be at least 1")
        
        # Validate armor class if provided
        if template.armor_class is not None and (template.armor_class < 1 or template.armor_class > 30):
            errors.append("Armor class must be between 1 and 30")
        
        # Validate speed if provided
        if template.speed is not None and template.speed < 0:
            errors.append("Speed cannot be negative")
        
        # Validate equipment format
        for i, item in enumerate(template.equipment):
            if not isinstance(item, dict):
                errors.append(f"Equipment item {i} must be an object")
            elif 'name' not in item:
                errors.append(f"Equipment item {i} must have a name")
        
        # Validate features format
        for i, feature in enumerate(template.features):
            if not isinstance(feature, dict):
                errors.append(f"Feature {i} must be an object")
            elif 'name' not in feature:
                errors.append(f"Feature {i} must have a name")
        
        if errors:
            raise TemplateValidationError(f"Template validation failed: {'; '.join(errors)}")
    
    def get_templates(self, force_refresh: bool = False) -> Dict[str, CharacterTemplate]:
        """Get all available templates."""
        self.scan_templates(force_refresh)
        return self._template_cache.copy()
    
    def get_template(self, template_id: str) -> Optional[CharacterTemplate]:
        """Get a specific template by ID."""
        self.scan_templates()
        return self._template_cache.get(template_id)
    
    def get_template_by_name(self, name: str) -> Optional[CharacterTemplate]:
        """Get a template by name."""
        self.scan_templates()
        for template in self._template_cache.values():
            if template.name.lower() == name.lower():
                return template
        return None
    
    def create_character_from_template(
        self,
        template_id: str,
        character_name: str,
        customizations: Optional[Dict[str, Any]] = None,
        ability_score_method: AbilityScoreMethod = AbilityScoreMethod.STANDARD_ARRAY,
        custom_ability_scores: Optional[Dict[str, int]] = None
    ) -> Character:
        """Create a character from a template with optional customizations."""
        
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        customizations = customizations or {}
        
        # Determine ability scores
        if custom_ability_scores:
            ability_scores = AbilityScores(**custom_ability_scores)
        elif template.ability_scores:
            # Use template's ability scores
            template_scores = template.ability_scores.copy()
            # Fill in missing scores with defaults
            for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                if ability not in template_scores:
                    template_scores[ability] = 10
            ability_scores = AbilityScores(**template_scores)
        else:
            # Generate new ability scores
            ability_scores = self.character_service.generate_ability_scores(ability_score_method)
        
        # Apply customizations to basic info
        race = customizations.get('race', template.race)
        character_class = customizations.get('character_class', template.character_class)
        background = customizations.get('background', template.background)
        level = customizations.get('level', template.level)
        
        # Create the character
        character = self.character_service.create_character(
            name=character_name,
            race=race,
            character_class=character_class,
            background=background,
            ability_scores=ability_scores,
            ability_score_method=ability_score_method
        )
        
        # Apply template-specific customizations
        self._apply_template_customizations(character, template, customizations)
        
        # Recalculate derived stats
        character.armor_class = character.calculate_armor_class()
        
        # Save the character
        self.character_service.save_character(character)
        
        return character
    
    def _apply_template_customizations(
        self,
        character: Character,
        template: CharacterTemplate,
        customizations: Dict[str, Any]
    ) -> None:
        """Apply template-specific customizations to a character."""
        
        # Override proficiencies if specified in template
        if template.skill_proficiencies:
            # Replace or merge based on customization
            if customizations.get('replace_skills', False):
                character.skill_proficiencies = template.skill_proficiencies.copy()
            else:
                # Add template skills that aren't already present
                for skill in template.skill_proficiencies:
                    if skill not in character.skill_proficiencies:
                        character.skill_proficiencies.append(skill)
        
        # Add template equipment
        if template.equipment:
            for item_data in template.equipment:
                equipment_item = self._create_equipment_from_template(item_data)
                
                # Check if item already exists (avoid duplicates)
                existing_item = next(
                    (item for item in character.equipment if item.name == equipment_item.name),
                    None
                )
                
                if existing_item:
                    # Update quantity if it's the same item
                    existing_item.quantity += equipment_item.quantity
                else:
                    character.equipment.append(equipment_item)
        
        # Add template features
        if template.features:
            for feature_data in template.features:
                feature = self._create_feature_from_template(feature_data)
                
                # Check if feature already exists
                existing_feature = next(
                    (f for f in character.features if f.name == feature.name),
                    None
                )
                
                if not existing_feature:
                    character.features.append(feature)
        
        # Apply template overrides
        if template.hit_points is not None:
            character.hit_points = template.hit_points
            character.max_hit_points = template.hit_points
        
        if template.speed is not None:
            character.speed = template.speed
        
        # Apply level if different
        if template.level != character.level and template.level > 1:
            # Level up to template level
            while character.level < template.level:
                self.character_service.level_up_character(character.id)
    
    def _create_equipment_from_template(self, item_data: Dict[str, Any]) -> EquipmentItem:
        """Create an EquipmentItem from template data."""
        return EquipmentItem(
            name=item_data.get("name", "Unknown Item"),
            item_type=item_data.get("type", "equipment"),
            description=item_data.get("description", ""),
            quantity=item_data.get("quantity", 1),
            weight=item_data.get("weight", 0.0),
            value_gp=item_data.get("value_gp", 0.0),
            properties=item_data.get("properties", {}),
            damage=item_data.get("damage"),
            damage_type=item_data.get("damage_type"),
            armor_class=item_data.get("ac"),
            ac_bonus=item_data.get("ac_bonus"),
            range_normal=item_data.get("range_normal"),
            range_long=item_data.get("range_long")
        )
    
    def _create_feature_from_template(self, feature_data: Dict[str, Any]) -> CharacterFeature:
        """Create a CharacterFeature from template data."""
        return CharacterFeature(
            name=feature_data.get("name", "Unknown Feature"),
            description=feature_data.get("description", ""),
            source=feature_data.get("source", "template"),
            level_acquired=feature_data.get("level_acquired", 1),
            uses_per_rest=feature_data.get("uses_per_rest"),
            rest_type=feature_data.get("rest_type")
        )
    
    def save_template(self, template: CharacterTemplate, template_id: Optional[str] = None) -> bool:
        """Save a template to a YAML file."""
        try:
            # Validate before saving
            self.validate_template(template)
            
            # Generate filename
            if template_id:
                filename = f"{template_id}.yaml"
            else:
                filename = f"{template.name.lower().replace(' ', '_')}.yaml"
            
            file_path = self.templates_dir / filename
            
            # Convert to dict and clean up for YAML
            template_data = template.to_dict()
            
            # Remove None values and empty lists
            template_data = {k: v for k, v in template_data.items() if v is not None and v != []}
            
            # Structure proficiencies nicely for YAML
            if any(key.endswith('_proficiencies') for key in template_data.keys()):
                proficiencies = {}
                
                for key in list(template_data.keys()):
                    if key.endswith('_proficiencies') and template_data[key]:
                        prof_type = key.replace('_proficiencies', '')
                        if prof_type == 'saving_throw':
                            prof_type = 'saving_throws'
                        elif prof_type == 'skill':
                            prof_type = 'skills'
                        elif prof_type == 'armor':
                            prof_type = 'armor'
                        elif prof_type == 'weapon':
                            prof_type = 'weapons'
                        elif prof_type == 'tool':
                            prof_type = 'tools'
                        
                        proficiencies[prof_type] = template_data.pop(key)
                
                if proficiencies:
                    template_data['proficiencies'] = proficiencies
            
            # Write to YAML file
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, indent=2)
            
            # Update cache
            cache_key = file_path.stem
            template.file_path = str(file_path)
            self._template_cache[cache_key] = template
            
            logger.info(f"Saved template '{template.name}' to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template file."""
        try:
            template = self.get_template(template_id)
            if not template or not template.file_path:
                return False
            
            file_path = Path(template.file_path)
            if file_path.exists():
                file_path.unlink()
                
                # Remove from cache
                if template_id in self._template_cache:
                    del self._template_cache[template_id]
                
                logger.info(f"Deleted template: {template_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to delete template {template_id}: {e}")
        
        return False
    
    def create_template_from_character(self, character: Character, template_name: str) -> CharacterTemplate:
        """Create a template from an existing character."""
        
        # Convert character equipment to template format
        equipment_data = []
        for item in character.equipment:
            item_dict = {
                "name": item.name,
                "type": item.item_type,
                "description": item.description
            }
            
            if item.quantity > 1:
                item_dict["quantity"] = item.quantity
            if item.damage:
                item_dict["damage"] = item.damage
            if item.damage_type:
                item_dict["damage_type"] = item.damage_type
            if item.armor_class:
                item_dict["ac"] = item.armor_class
            if item.ac_bonus:
                item_dict["ac_bonus"] = item.ac_bonus
            
            equipment_data.append(item_dict)
        
        # Convert character features to template format
        features_data = []
        for feature in character.features:
            feature_dict = {
                "name": feature.name,
                "description": feature.description,
                "source": feature.source
            }
            
            if feature.level_acquired > 1:
                feature_dict["level_acquired"] = feature.level_acquired
            if feature.uses_per_rest:
                feature_dict["uses_per_rest"] = feature.uses_per_rest
            if feature.rest_type:
                feature_dict["rest_type"] = feature.rest_type
            
            features_data.append(feature_dict)
        
        # Create template
        template = CharacterTemplate(
            name=template_name,
            description=f"Template created from character {character.name}",
            race=character.race,
            character_class=character.character_class,
            background=character.background,
            level=character.level,
            ability_scores=character.ability_scores.to_dict(),
            skill_proficiencies=character.skill_proficiencies.copy(),
            saving_throw_proficiencies=character.saving_throw_proficiencies.copy(),
            armor_proficiencies=character.armor_proficiencies.copy(),
            weapon_proficiencies=character.weapon_proficiencies.copy(),
            tool_proficiencies=character.tool_proficiencies.copy(),
            languages=character.languages.copy(),
            equipment=equipment_data,
            features=features_data,
            hit_points=character.max_hit_points,
            armor_class=character.armor_class,
            speed=character.speed
        )
        
        return template
    
    def get_template_summary(self) -> Dict[str, Any]:
        """Get a summary of all available templates."""
        self.scan_templates()
        
        templates_info = []
        for template_id, template in self._template_cache.items():
            templates_info.append({
                "id": template_id,
                "name": template.name,
                "description": template.description,
                "race": template.race,
                "class": template.character_class,
                "background": template.background,
                "level": template.level
            })
        
        return {
            "total_templates": len(self._template_cache),
            "templates": templates_info
        }


# Global service instance
template_engine = TemplateEngine() 