"""Comprehensive D&D 5e character validation system."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum

from app.services.character_service import (
    Character, AbilityScores, CharacterService, AbilityScoreMethod,
    CharacterClass, CharacterRace, CharacterBackground
)

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation message severity levels."""
    ERROR = "error"       # Rule violations that make character invalid
    WARNING = "warning"   # Unusual but not invalid configurations
    INFO = "info"         # Informational notes
    SUGGESTION = "suggestion"  # Optimization suggestions


@dataclass
class ValidationMessage:
    """A validation message with context."""
    severity: ValidationSeverity
    category: str  # e.g., "ability_scores", "equipment", "class_features"
    message: str
    context: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of character validation."""
    is_valid: bool
    messages: List[ValidationMessage]
    errors: List[str]  # Error messages for backwards compatibility
    warnings: List[str]
    infos: List[str]
    suggestions: List[str]
    
    def add_message(self, message: ValidationMessage):
        """Add a validation message."""
        self.messages.append(message)
        
        if message.severity == ValidationSeverity.ERROR:
            self.errors.append(message.message)
            self.is_valid = False
        elif message.severity == ValidationSeverity.WARNING:
            self.warnings.append(message.message)
        elif message.severity == ValidationSeverity.INFO:
            self.infos.append(message.message)
        elif message.severity == ValidationSeverity.SUGGESTION:
            self.suggestions.append(message.message)


class D5eValidationSystem:
    """Comprehensive D&D 5e character validation system."""
    
    # D&D 5e Rules Constants
    MAX_SKILL_PROFICIENCIES_BY_CLASS = {
        CharacterClass.BARBARIAN: 2,
        CharacterClass.BARD: 3,
        CharacterClass.CLERIC: 2,
        CharacterClass.DRUID: 2,
        CharacterClass.FIGHTER: 2,
        CharacterClass.MONK: 2,
        CharacterClass.PALADIN: 2,
        CharacterClass.RANGER: 3,
        CharacterClass.ROGUE: 4,
        CharacterClass.SORCERER: 2,
        CharacterClass.WARLOCK: 2,
        CharacterClass.WIZARD: 2
    }
    
    CLASS_SAVING_THROWS = {
        CharacterClass.BARBARIAN: ["strength", "constitution"],
        CharacterClass.BARD: ["dexterity", "charisma"],
        CharacterClass.CLERIC: ["wisdom", "charisma"],
        CharacterClass.DRUID: ["intelligence", "wisdom"],
        CharacterClass.FIGHTER: ["strength", "constitution"],
        CharacterClass.MONK: ["strength", "dexterity"],
        CharacterClass.PALADIN: ["wisdom", "charisma"],
        CharacterClass.RANGER: ["strength", "dexterity"],
        CharacterClass.ROGUE: ["dexterity", "intelligence"],
        CharacterClass.SORCERER: ["constitution", "charisma"],
        CharacterClass.WARLOCK: ["wisdom", "charisma"],
        CharacterClass.WIZARD: ["intelligence", "wisdom"]
    }
    
    CLASS_AVAILABLE_SKILLS = {
        CharacterClass.BARBARIAN: ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"],
        CharacterClass.BARD: ["Deception", "History", "Investigation", "Persuasion", "Performance", "Sleight of Hand"],
        CharacterClass.CLERIC: ["History", "Insight", "Medicine", "Persuasion", "Religion"],
        CharacterClass.DRUID: ["Arcana", "Animal Handling", "Insight", "Medicine", "Nature", "Perception", "Religion", "Survival"],
        CharacterClass.FIGHTER: ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"],
        CharacterClass.MONK: ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"],
        CharacterClass.PALADIN: ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"],
        CharacterClass.RANGER: ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"],
        CharacterClass.ROGUE: ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"],
        CharacterClass.SORCERER: ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"],
        CharacterClass.WARLOCK: ["Arcana", "Deception", "History", "Intimidation", "Investigation", "Nature", "Religion"],
        CharacterClass.WIZARD: ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"]
    }
    
    RACIAL_ABILITY_BONUSES = {
        CharacterRace.HUMAN: {"strength": 1, "dexterity": 1, "constitution": 1, "intelligence": 1, "wisdom": 1, "charisma": 1},
        CharacterRace.ELF: {"dexterity": 2},
        CharacterRace.DWARF: {"constitution": 2},
        CharacterRace.HALFLING: {"dexterity": 2},
        CharacterRace.DRAGONBORN: {"strength": 2, "charisma": 1},
        CharacterRace.GNOME: {"intelligence": 2},
        CharacterRace.HALF_ELF: {"charisma": 2},  # Plus 2 others of choice
        CharacterRace.HALF_ORC: {"strength": 2, "constitution": 1},
        CharacterRace.TIEFLING: {"intelligence": 1, "charisma": 2}
    }
    
    def __init__(self, character_service: Optional[CharacterService] = None):
        self.character_service = character_service or CharacterService()
    
    def validate_character(self, character: Character, comprehensive: bool = True) -> ValidationResult:
        """Perform comprehensive character validation."""
        result = ValidationResult(
            is_valid=True,
            messages=[],
            errors=[],
            warnings=[],
            infos=[],
            suggestions=[]
        )
        
        # Basic validation (always performed)
        self._validate_basic_info(character, result)
        self._validate_ability_scores(character, result)
        self._validate_level_and_progression(character, result)
        self._validate_hit_points(character, result)
        
        if comprehensive:
            # Comprehensive validation
            self._validate_class_features(character, result)
            self._validate_racial_features(character, result)
            self._validate_background_features(character, result)
            self._validate_proficiencies(character, result)
            self._validate_equipment(character, result)
            self._validate_spell_constraints(character, result)
            self._validate_multiclass_requirements(character, result)
            self._suggest_optimizations(character, result)
        
        return result
    
    def _validate_basic_info(self, character: Character, result: ValidationResult):
        """Validate basic character information."""
        # Name validation
        if not character.name or not character.name.strip():
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="basic_info",
                message="Character name cannot be empty"
            ))
        elif len(character.name.strip()) > 50:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                category="basic_info",
                message="Character name is very long (over 50 characters)"
            ))
        
        # Race validation
        try:
            CharacterRace(character.race.lower().replace(" ", "_"))
        except ValueError:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="basic_info",
                message=f"Invalid race: {character.race}",
                suggestion="Use a valid D&D 5e race"
            ))
        
        # Class validation
        try:
            CharacterClass(character.character_class.lower())
        except ValueError:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="basic_info",
                message=f"Invalid class: {character.character_class}",
                suggestion="Use a valid D&D 5e class"
            ))
        
        # Background validation
        try:
            CharacterBackground(character.background.lower().replace(" ", "_"))
        except ValueError:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="basic_info",
                message=f"Invalid background: {character.background}",
                suggestion="Use a valid D&D 5e background"
            ))
    
    def _validate_ability_scores(self, character: Character, result: ValidationResult):
        """Validate ability scores against D&D 5e rules."""
        abilities = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        
        for ability in abilities:
            score = getattr(character.ability_scores, ability)
            
            # Basic range check
            if score < 1 or score > 30:
                result.add_message(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    category="ability_scores",
                    message=f"{ability.title()} score {score} is outside valid range (1-30)"
                ))
            elif score < 8:
                result.add_message(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    category="ability_scores",
                    message=f"{ability.title()} score {score} is unusually low (below 8)",
                    suggestion="Consider if this extremely low score is intentional"
                ))
            elif score > 20 and character.level < 20:
                result.add_message(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    category="ability_scores",
                    message=f"{ability.title()} score {score} is very high for level {character.level}",
                    context={"ability": ability, "score": score, "level": character.level}
                ))
        
        # Check for valid ability score generation patterns
        self._validate_ability_score_patterns(character, result)
    
    def _validate_ability_score_patterns(self, character: Character, result: ValidationResult):
        """Validate ability scores follow valid generation patterns."""
        scores = [
            character.ability_scores.strength,
            character.ability_scores.dexterity,
            character.ability_scores.constitution,
            character.ability_scores.intelligence,
            character.ability_scores.wisdom,
            character.ability_scores.charisma
        ]
        
        # Check for standard array (before racial bonuses)
        standard_array = sorted([15, 14, 13, 12, 10, 8])
        
        # Check for point buy validity (complex calculation)
        point_buy_valid = self._check_point_buy_validity(character)
        
        # Check if scores look rolled (more variation)
        score_variance = max(scores) - min(scores)
        
        if sorted(scores) == standard_array:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.INFO,
                category="ability_scores",
                message="Ability scores match standard array"
            ))
        elif point_buy_valid:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.INFO,
                category="ability_scores",
                message="Ability scores are valid for point buy"
            ))
        elif score_variance > 10:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.INFO,
                category="ability_scores",
                message="Ability scores appear to be rolled (high variance)",
                context={"variance": score_variance}
            ))
    
    def _check_point_buy_validity(self, character: Character) -> bool:
        """Check if ability scores could be valid point buy."""
        try:
            # This is complex due to racial bonuses, so we'll do a simplified check
            base_scores = self._estimate_base_scores(character)
            if not base_scores:
                return False
            
            # Check if base scores are in point buy range
            for score in base_scores:
                if score < 8 or score > 15:
                    return False
            
            # Calculate point buy cost
            total_cost = sum(self.character_service.POINT_BUY_COSTS.get(score, 999) for score in base_scores)
            return total_cost <= self.character_service.POINT_BUY_BUDGET
            
        except Exception:
            return False
    
    def _estimate_base_scores(self, character: Character) -> Optional[List[int]]:
        """Estimate base ability scores before racial bonuses."""
        try:
            race_enum = CharacterRace(character.race.lower().replace(" ", "_"))
            racial_bonuses = self.RACIAL_ABILITY_BONUSES.get(race_enum, {})
            
            current_scores = character.ability_scores.to_dict()
            base_scores = []
            
            for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
                current = current_scores[ability]
                bonus = racial_bonuses.get(ability, 0)
                base_scores.append(current - bonus)
            
            return base_scores
            
        except Exception:
            return None
    
    def _validate_level_and_progression(self, character: Character, result: ValidationResult):
        """Validate character level and progression."""
        if character.level < 1 or character.level > 20:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="level",
                message=f"Level {character.level} is outside valid range (1-20)"
            ))
        
        # Check proficiency bonus
        expected_proficiency = self.character_service.PROFICIENCY_BONUS_BY_LEVEL.get(character.level, 2)
        if character.proficiency_bonus != expected_proficiency:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="level",
                message=f"Proficiency bonus {character.proficiency_bonus} doesn't match level {character.level} (expected {expected_proficiency})"
            ))
    
    def _validate_hit_points(self, character: Character, result: ValidationResult):
        """Validate hit points calculations."""
        if character.hit_points < 0:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="hit_points",
                message="Current hit points cannot be negative"
            ))
        
        if character.max_hit_points < 1:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="hit_points",
                message="Maximum hit points must be at least 1"
            ))
        
        if character.hit_points > character.max_hit_points:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                category="hit_points",
                message="Current hit points cannot exceed maximum hit points"
            ))
        
        # Validate max hit points calculation
        try:
            class_enum = CharacterClass(character.character_class.lower())
            hit_die = self.character_service.HIT_DICE_BY_CLASS.get(class_enum, 8)
            con_modifier = character.get_ability_modifier("constitution")
            
            # Calculate expected minimum and maximum HP
            min_hp = character.level + (con_modifier * character.level)  # All 1s on hit die
            max_hp = (hit_die * character.level) + (con_modifier * character.level)  # Max on all hit dice
            
            if character.max_hit_points < min_hp:
                result.add_message(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    category="hit_points",
                    message=f"Maximum hit points {character.max_hit_points} is too low for level {character.level} (minimum {min_hp})"
                ))
            elif character.max_hit_points > max_hp:
                result.add_message(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    category="hit_points",
                    message=f"Maximum hit points {character.max_hit_points} is very high for level {character.level} (maximum theoretical {max_hp})"
                ))
                
        except Exception as e:
            logger.debug(f"Could not validate hit points calculation: {e}")
    
    def _validate_class_features(self, character: Character, result: ValidationResult):
        """Validate class-specific features and requirements."""
        try:
            class_enum = CharacterClass(character.character_class.lower())
            
            # Check saving throw proficiencies
            expected_saves = self.CLASS_SAVING_THROWS.get(class_enum, [])
            for save in expected_saves:
                if save not in character.saving_throw_proficiencies:
                    result.add_message(ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        category="class_features",
                        message=f"{character.character_class.title()} should have {save.title()} saving throw proficiency"
                    ))
            
            # Check for unexpected saving throw proficiencies
            for save in character.saving_throw_proficiencies:
                if save not in expected_saves:
                    result.add_message(ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        category="class_features",
                        message=f"Unexpected {save.title()} saving throw proficiency for {character.character_class.title()}",
                        suggestion="This might be from a feat or multiclassing"
                    ))
                    
        except Exception as e:
            logger.debug(f"Could not validate class features: {e}")
    
    def _validate_racial_features(self, character: Character, result: ValidationResult):
        """Validate racial features and bonuses."""
        try:
            race_enum = CharacterRace(character.race.lower().replace(" ", "_"))
            
            # Check racial ability score bonuses
            expected_bonuses = self.RACIAL_ABILITY_BONUSES.get(race_enum, {})
            base_scores = self._estimate_base_scores(character)
            
            if base_scores:
                current_scores = character.ability_scores.to_dict()
                abilities = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
                
                for i, ability in enumerate(abilities):
                    expected_bonus = expected_bonuses.get(ability, 0)
                    actual_bonus = current_scores[ability] - base_scores[i]
                    
                    if expected_bonus > 0 and actual_bonus < expected_bonus:
                        result.add_message(ValidationMessage(
                            severity=ValidationSeverity.WARNING,
                            category="racial_features",
                            message=f"Missing expected +{expected_bonus} racial bonus to {ability.title()} for {character.race.title()}"
                        ))
                        
        except Exception as e:
            logger.debug(f"Could not validate racial features: {e}")
    
    def _validate_background_features(self, character: Character, result: ValidationResult):
        """Validate background features and proficiencies."""
        # Basic validation - in a full implementation, this would be more detailed
        if not character.skill_proficiencies:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                category="background_features",
                message="Character has no skill proficiencies, which is unusual"
            ))
    
    def _validate_proficiencies(self, character: Character, result: ValidationResult):
        """Validate skill and other proficiencies."""
        try:
            class_enum = CharacterClass(character.character_class.lower())
            
            # Check skill proficiency count
            max_skills = self.MAX_SKILL_PROFICIENCIES_BY_CLASS.get(class_enum, 2)
            class_skills = len([skill for skill in character.skill_proficiencies 
                              if skill in self.CLASS_AVAILABLE_SKILLS.get(class_enum, [])])
            
            if class_skills > max_skills:
                result.add_message(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    category="proficiencies",
                    message=f"{character.character_class.title()} can only choose {max_skills} class skill proficiencies, but has {class_skills}"
                ))
            
            # Check for invalid skill choices
            available_skills = self.CLASS_AVAILABLE_SKILLS.get(class_enum, [])
            for skill in character.skill_proficiencies:
                # Allow skills from background and racial features
                if skill not in available_skills and character.skill_proficiencies.count(skill) > 1:
                    result.add_message(ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        category="proficiencies",
                        message=f"Skill proficiency '{skill}' might not be available to {character.character_class.title()}",
                        suggestion="Verify this comes from background, race, or feat"
                    ))
                    
        except Exception as e:
            logger.debug(f"Could not validate proficiencies: {e}")
    
    def _validate_equipment(self, character: Character, result: ValidationResult):
        """Validate equipment and encumbrance."""
        # Check for conflicting armor
        armor_count = sum(1 for item in character.equipment if item.item_type == "armor")
        if armor_count > 1:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                category="equipment",
                message="Character has multiple armor items equipped",
                suggestion="Only one armor can be worn at a time"
            ))
        
        # Check shield usage
        shield_count = sum(1 for item in character.equipment if item.item_type == "shield")
        if shield_count > 1:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                category="equipment",
                message="Character has multiple shields",
                suggestion="Only one shield can be used at a time"
            ))
        
        # Basic weight calculation (simplified)
        total_weight = sum(item.weight * item.quantity for item in character.equipment if item.weight)
        strength_score = character.ability_scores.strength
        carry_capacity = strength_score * 15  # Basic carry capacity
        
        if total_weight > carry_capacity:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                category="equipment",
                message=f"Equipment weight ({total_weight} lbs) exceeds carry capacity ({carry_capacity} lbs)",
                context={"weight": total_weight, "capacity": carry_capacity}
            ))
    
    def _validate_spell_constraints(self, character: Character, result: ValidationResult):
        """Validate spellcasting constraints (placeholder)."""
        # This would validate spell slots, known spells, etc.
        # For now, just a basic check
        pass
    
    def _validate_multiclass_requirements(self, character: Character, result: ValidationResult):
        """Validate multiclassing requirements (placeholder)."""
        # This would check ability score requirements for multiclassing
        # For now, assume single class
        pass
    
    def _suggest_optimizations(self, character: Character, result: ValidationResult):
        """Suggest character optimizations."""
        # Suggest ability score improvements
        for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            score = getattr(character.ability_scores, ability)
            if score in [13, 15, 17, 19]:  # Odd scores that could be improved
                result.add_message(ValidationMessage(
                    severity=ValidationSeverity.SUGGESTION,
                    category="optimization",
                    message=f"Consider increasing {ability.title()} from {score} to {score + 1} for a better modifier",
                    context={"ability": ability, "current_score": score}
                ))
        
        # Suggest equipment optimizations
        has_armor = any(item.item_type == "armor" for item in character.equipment)
        if not has_armor:
            result.add_message(ValidationMessage(
                severity=ValidationSeverity.SUGGESTION,
                category="optimization",
                message="Character has no armor equipped, consider adding armor for better AC"
            ))


# Global validator instance
validation_system = D5eValidationSystem() 