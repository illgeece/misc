"""Character creation wizard for step-by-step D&D 5e character creation."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum

from app.services.character_service import (
    Character, AbilityScores, CharacterService, AbilityScoreMethod,
    CharacterClass, CharacterRace, CharacterBackground
)
from app.services.template_engine import TemplateEngine, CharacterTemplate
from app.services.dice_engine import dice_engine

logger = logging.getLogger(__name__)


class CreationStep(Enum):
    """Steps in the character creation process."""
    TEMPLATE_SELECTION = "template_selection"
    BASIC_INFO = "basic_info"
    RACE_SELECTION = "race_selection"
    CLASS_SELECTION = "class_selection"
    BACKGROUND_SELECTION = "background_selection"
    ABILITY_SCORES = "ability_scores"
    SKILLS = "skills"
    EQUIPMENT = "equipment"
    FINALIZATION = "finalization"


@dataclass
class CreationChoices:
    """Container for choices made during character creation."""
    
    # Template
    template_id: Optional[str] = None
    template: Optional[CharacterTemplate] = None
    
    # Basic info
    name: str = ""
    
    # Character options
    race: str = ""
    character_class: str = ""
    background: str = ""
    
    # Ability scores
    ability_score_method: AbilityScoreMethod = AbilityScoreMethod.STANDARD_ARRAY
    ability_scores: Optional[AbilityScores] = None
    
    # Skills (for classes that allow choice)
    chosen_skills: List[str] = field(default_factory=list)
    
    # Equipment choices (for classes with multiple starting options)
    equipment_choices: Dict[str, str] = field(default_factory=dict)
    
    # Custom modifications
    custom_modifications: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "race": self.race,
            "character_class": self.character_class,
            "background": self.background,
            "ability_score_method": self.ability_score_method.value if self.ability_score_method else None,
            "ability_scores": self.ability_scores.to_dict() if self.ability_scores else None,
            "chosen_skills": self.chosen_skills,
            "equipment_choices": self.equipment_choices,
            "custom_modifications": self.custom_modifications
        }


@dataclass
class CreationSession:
    """A character creation session with state tracking."""
    
    session_id: str
    current_step: CreationStep = CreationStep.TEMPLATE_SELECTION
    choices: CreationChoices = field(default_factory=CreationChoices)
    created_character: Optional[Character] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Add an error to the session."""
        self.errors.append(error)
        logger.warning(f"Creation session {self.session_id} error: {error}")
    
    def add_warning(self, warning: str):
        """Add a warning to the session."""
        self.warnings.append(warning)
        logger.info(f"Creation session {self.session_id} warning: {warning}")
    
    def clear_errors(self):
        """Clear all errors."""
        self.errors.clear()
    
    def clear_warnings(self):
        """Clear all warnings."""
        self.warnings.clear()


class CharacterCreationWizard:
    """Wizard service for step-by-step character creation."""
    
    def __init__(self, character_service: Optional[CharacterService] = None, template_engine: Optional[TemplateEngine] = None):
        self.character_service = character_service or CharacterService()
        self.template_engine = template_engine or TemplateEngine()
        
        # Active creation sessions
        self._sessions: Dict[str, CreationSession] = {}
    
    def start_creation_session(self) -> CreationSession:
        """Start a new character creation session."""
        session_id = str(uuid.uuid4())
        session = CreationSession(session_id=session_id)
        self._sessions[session_id] = session
        
        logger.info(f"Started character creation session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[CreationSession]:
        """Get an existing creation session."""
        return self._sessions.get(session_id)
    
    def end_session(self, session_id: str) -> bool:
        """End a creation session and clean up."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Ended character creation session: {session_id}")
            return True
        return False
    
    def get_available_templates(self) -> Dict[str, Any]:
        """Get available character templates for selection."""
        return self.template_engine.get_template_summary()
    
    def set_template(self, session_id: str, template_id: Optional[str]) -> Tuple[bool, Dict[str, Any]]:
        """Set the character template for creation."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        if template_id:
            template = self.template_engine.get_template(template_id)
            if not template:
                session.add_error(f"Template not found: {template_id}")
                return False, {"error": "Template not found"}
            
            session.choices.template_id = template_id
            session.choices.template = template
            
            # Pre-fill choices from template
            if template.race:
                session.choices.race = template.race
            if template.character_class:
                session.choices.character_class = template.character_class
            if template.background:
                session.choices.background = template.background
            if template.ability_scores:
                session.choices.ability_scores = AbilityScores(**template.ability_scores)
            
            logger.info(f"Session {session_id} selected template: {template.name}")
        else:
            # No template selected
            session.choices.template_id = None
            session.choices.template = None
        
        # Move to next step
        session.current_step = CreationStep.BASIC_INFO
        
        return True, self.get_current_step_info(session_id)
    
    def set_basic_info(self, session_id: str, name: str) -> Tuple[bool, Dict[str, Any]]:
        """Set basic character information."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate name
        if not name or not name.strip():
            session.add_error("Character name is required")
            return False, {"error": "Character name is required"}
        
        if len(name.strip()) > 50:
            session.add_error("Character name must be 50 characters or less")
            return False, {"error": "Character name too long"}
        
        session.choices.name = name.strip()
        
        # Move to next step
        session.current_step = CreationStep.RACE_SELECTION
        
        logger.info(f"Session {session_id} set name: {name}")
        return True, self.get_current_step_info(session_id)
    
    def set_race(self, session_id: str, race: str) -> Tuple[bool, Dict[str, Any]]:
        """Set character race."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate race
        try:
            CharacterRace(race.lower().replace(" ", "_"))
        except ValueError:
            session.add_error(f"Invalid race: {race}")
            return False, {"error": "Invalid race"}
        
        session.choices.race = race
        
        # Move to next step
        session.current_step = CreationStep.CLASS_SELECTION
        
        logger.info(f"Session {session_id} set race: {race}")
        return True, self.get_current_step_info(session_id)
    
    def set_class(self, session_id: str, character_class: str) -> Tuple[bool, Dict[str, Any]]:
        """Set character class."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate class
        try:
            CharacterClass(character_class.lower())
        except ValueError:
            session.add_error(f"Invalid class: {character_class}")
            return False, {"error": "Invalid class"}
        
        session.choices.character_class = character_class
        
        # Move to next step
        session.current_step = CreationStep.BACKGROUND_SELECTION
        
        logger.info(f"Session {session_id} set class: {character_class}")
        return True, self.get_current_step_info(session_id)
    
    def set_background(self, session_id: str, background: str) -> Tuple[bool, Dict[str, Any]]:
        """Set character background."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate background
        try:
            CharacterBackground(background.lower().replace(" ", "_"))
        except ValueError:
            session.add_error(f"Invalid background: {background}")
            return False, {"error": "Invalid background"}
        
        session.choices.background = background
        
        # Move to next step
        session.current_step = CreationStep.ABILITY_SCORES
        
        logger.info(f"Session {session_id} set background: {background}")
        return True, self.get_current_step_info(session_id)
    
    def set_ability_score_method(self, session_id: str, method: str) -> Tuple[bool, Dict[str, Any]]:
        """Set the ability score generation method."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        try:
            score_method = AbilityScoreMethod(method)
        except ValueError:
            session.add_error(f"Invalid ability score method: {method}")
            return False, {"error": "Invalid ability score method"}
        
        session.choices.ability_score_method = score_method
        
        # Generate ability scores based on method
        if score_method in [AbilityScoreMethod.ROLL_4D6_DROP_LOWEST, AbilityScoreMethod.ROLL_3D6]:
            # Generate rolled scores
            session.choices.ability_scores = self.character_service.generate_ability_scores(score_method)
        elif score_method == AbilityScoreMethod.STANDARD_ARRAY:
            # Use standard array
            session.choices.ability_scores = self.character_service.generate_ability_scores(score_method)
        elif score_method == AbilityScoreMethod.POINT_BUY:
            # Start with base values for point buy
            session.choices.ability_scores = AbilityScores(
                strength=8, dexterity=8, constitution=8,
                intelligence=8, wisdom=8, charisma=8
            )
        
        logger.info(f"Session {session_id} set ability score method: {method}")
        return True, self.get_current_step_info(session_id)
    
    def set_ability_scores(self, session_id: str, scores: Dict[str, int]) -> Tuple[bool, Dict[str, Any]]:
        """Set ability scores manually."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate ability scores
        valid_abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        
        for ability in valid_abilities:
            if ability not in scores:
                session.add_error(f"Missing ability score: {ability}")
        
        for ability, score in scores.items():
            if ability not in valid_abilities:
                session.add_error(f"Invalid ability: {ability}")
            elif not isinstance(score, int) or score < 1 or score > 30:
                session.add_error(f"Invalid {ability} score: {score} (must be 1-30)")
        
        # Validate point buy if that's the method
        if session.choices.ability_score_method == AbilityScoreMethod.POINT_BUY:
            ability_scores = AbilityScores(**scores)
            is_valid, error = self.character_service.validate_point_buy(ability_scores)
            if not is_valid:
                session.add_error(f"Point buy validation failed: {error}")
        
        if session.errors:
            return False, {"errors": session.errors}
        
        session.choices.ability_scores = AbilityScores(**scores)
        
        # Move to next step
        session.current_step = CreationStep.SKILLS
        
        return True, self.get_current_step_info(session_id)
    
    def generate_ability_scores(self, session_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Generate ability scores based on the selected method."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        if not session.choices.ability_score_method:
            session.add_error("Ability score method must be set first")
            return False, {"error": "Ability score method not set"}
        
        try:
            # Generate scores using the character service
            scores = self.character_service.generate_ability_scores(session.choices.ability_score_method)
            session.choices.ability_scores = scores
            
            # Move to next step
            session.current_step = CreationStep.SKILLS
            
            return True, {
                "ability_scores": scores.to_dict(),
                "method": session.choices.ability_score_method.value,
                "next_step": session.current_step.value
            }
            
        except Exception as e:
            session.add_error(f"Failed to generate ability scores: {str(e)}")
            return False, {"error": str(e)}
    
    def roll_ability_scores(self, session_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Roll new ability scores using dice."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Use the method specified
        method = session.choices.ability_score_method
        
        if method not in [AbilityScoreMethod.ROLL_4D6_DROP_LOWEST, AbilityScoreMethod.ROLL_3D6]:
            session.add_error("Cannot roll ability scores with current method")
            return False, {"error": "Cannot roll with current method"}
        
        # Generate new scores
        session.choices.ability_scores = self.character_service.generate_ability_scores(method)
        
        logger.info(f"Session {session_id} rolled new ability scores")
        return True, self.get_current_step_info(session_id)
    
    def roll_ability_scores_with_details(self, session_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Roll new ability scores with detailed breakdown of each roll."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Use the method specified
        method = session.choices.ability_score_method
        
        if method not in [AbilityScoreMethod.ROLL_4D6_DROP_LOWEST, AbilityScoreMethod.ROLL_3D6]:
            session.add_error("Cannot roll ability scores with current method")
            return False, {"error": "Cannot roll with current method"}
        
        # Roll each ability score with detailed breakdown
        abilities = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        roll_details = []
        scores = {}
        
        dice_expression = "4d6dl1" if method == AbilityScoreMethod.ROLL_4D6_DROP_LOWEST else "3d6"
        
        for ability in abilities:
            try:
                result = dice_engine.execute_roll(dice_expression)
                scores[ability] = result.total
                
                roll_details.append({
                    "ability": ability,
                    "expression": dice_expression,
                    "total": result.total,
                    "dice_results": result.dice_results,
                    "breakdown": result.breakdown,
                    "timestamp": result.timestamp
                })
                
                logger.debug(f"Rolled {ability}: {result.total} from {dice_expression}")
                
            except Exception as e:
                session.add_error(f"Failed to roll {ability}: {e}")
                return False, {"error": f"Failed to roll ability scores: {e}"}
        
        # Create ability scores object
        session.choices.ability_scores = AbilityScores(**scores)
        
        logger.info(f"Session {session_id} rolled detailed ability scores")
        
        # Return detailed results
        return True, {
            "session_info": self.get_current_step_info(session_id),
            "roll_details": roll_details,
            "total_scores": scores,
            "method": method.value,
            "summary": {
                "highest": max(scores.values()),
                "lowest": min(scores.values()),
                "average": round(sum(scores.values()) / len(scores), 1),
                "total": sum(scores.values())
            }
        }
    
    def reroll_single_ability(self, session_id: str, ability: str) -> Tuple[bool, Dict[str, Any]]:
        """Reroll a single ability score using dice."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate ability
        if ability not in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            session.add_error(f"Invalid ability: {ability}")
            return False, {"error": "Invalid ability"}
        
        # Check if we can reroll
        method = session.choices.ability_score_method
        if method not in [AbilityScoreMethod.ROLL_4D6_DROP_LOWEST, AbilityScoreMethod.ROLL_3D6]:
            session.add_error("Cannot reroll ability scores with current method")
            return False, {"error": "Cannot reroll with current method"}
        
        if not session.choices.ability_scores:
            session.add_error("No ability scores to reroll")
            return False, {"error": "No ability scores to reroll"}
        
        # Roll new value
        dice_expression = "4d6dl1" if method == AbilityScoreMethod.ROLL_4D6_DROP_LOWEST else "3d6"
        
        try:
            result = dice_engine.execute_roll(dice_expression)
            
            # Update the ability score
            setattr(session.choices.ability_scores, ability, result.total)
            
            logger.info(f"Session {session_id} rerolled {ability}: {result.total}")
            
            return True, {
                "session_info": self.get_current_step_info(session_id),
                "reroll_result": {
                    "ability": ability,
                    "new_value": result.total,
                    "expression": dice_expression,
                    "dice_results": result.dice_results,
                    "breakdown": result.breakdown,
                    "timestamp": result.timestamp
                }
            }
            
        except Exception as e:
            session.add_error(f"Failed to reroll {ability}: {e}")
            return False, {"error": f"Failed to reroll {ability}: {e}"}
    
    def get_dice_rolling_options(self, session_id: str) -> Dict[str, Any]:
        """Get available dice rolling options for ability scores."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        current_method = session.choices.ability_score_method
        
        options = {
            "current_method": current_method.value if current_method else None,
            "can_roll": current_method in [AbilityScoreMethod.ROLL_4D6_DROP_LOWEST, AbilityScoreMethod.ROLL_3D6],
            "can_reroll_individual": current_method in [AbilityScoreMethod.ROLL_4D6_DROP_LOWEST, AbilityScoreMethod.ROLL_3D6],
            "dice_expressions": {
                AbilityScoreMethod.ROLL_4D6_DROP_LOWEST.value: "4d6dl1",
                AbilityScoreMethod.ROLL_3D6.value: "3d6"
            },
            "roll_descriptions": {
                AbilityScoreMethod.ROLL_4D6_DROP_LOWEST.value: "Roll 4d6, drop the lowest die",
                AbilityScoreMethod.ROLL_3D6.value: "Roll 3d6 straight"
            }
        }
        
        if session.choices.ability_scores:
            options["current_scores"] = session.choices.ability_scores.to_dict()
            options["current_modifiers"] = session.choices.ability_scores.get_all_modifiers()
        
        return options
    
    def set_skills(self, session_id: str, skills: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Set skill proficiencies for classes that allow choice."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate skills based on class
        available_skills = self._get_available_skills_for_class(session.choices.character_class)
        required_count = self._get_skill_choice_count(session.choices.character_class)
        
        if len(skills) != required_count:
            session.add_error(f"Must choose exactly {required_count} skills")
            return False, {"error": f"Must choose exactly {required_count} skills"}
        
        for skill in skills:
            if skill not in available_skills:
                session.add_error(f"Invalid skill choice: {skill}")
                return False, {"error": f"Invalid skill choice: {skill}"}
        
        session.choices.chosen_skills = skills
        
        # Move to next step
        session.current_step = CreationStep.EQUIPMENT
        
        logger.info(f"Session {session_id} set skills: {skills}")
        return True, self.get_current_step_info(session_id)
    
    def set_equipment_choices(self, session_id: str, choices: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
        """Set equipment choices for classes with options."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # For now, just accept the choices (full validation would be more complex)
        session.choices.equipment_choices = choices
        
        # Move to final step
        session.current_step = CreationStep.FINALIZATION
        
        logger.info(f"Session {session_id} set equipment choices")
        return True, self.get_current_step_info(session_id)
    
    def finalize_character(self, session_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Create the final character from all choices."""
        session = self.get_session(session_id)
        if not session:
            return False, {"error": "Session not found"}
        
        session.clear_errors()
        
        # Validate all required choices are made
        if not session.choices.name:
            session.add_error("Character name is required")
        if not session.choices.race:
            session.add_error("Race selection is required")
        if not session.choices.character_class:
            session.add_error("Class selection is required")
        if not session.choices.background:
            session.add_error("Background selection is required")
        if not session.choices.ability_scores:
            session.add_error("Ability scores are required")
        
        if session.errors:
            return False, {"errors": session.errors}
        
        try:
            # Create character
            if session.choices.template_id:
                # Create from template with customizations
                customizations = {
                    'race': session.choices.race,
                    'character_class': session.choices.character_class,
                    'background': session.choices.background
                }
                
                character = self.template_engine.create_character_from_template(
                    template_id=session.choices.template_id,
                    character_name=session.choices.name,
                    customizations=customizations,
                    ability_score_method=session.choices.ability_score_method,
                    custom_ability_scores=session.choices.ability_scores.to_dict()
                )
            else:
                # Create from scratch
                character = self.character_service.create_character(
                    name=session.choices.name,
                    race=session.choices.race,
                    character_class=session.choices.character_class,
                    background=session.choices.background,
                    ability_scores=session.choices.ability_scores,
                    ability_score_method=session.choices.ability_score_method
                )
            
            # Apply skill choices if any
            if session.choices.chosen_skills:
                for skill in session.choices.chosen_skills:
                    if skill not in character.skill_proficiencies:
                        character.skill_proficiencies.append(skill)
            
            # Save the character
            self.character_service.save_character(character)
            
            session.created_character = character
            
            logger.info(f"Session {session_id} created character: {character.name} ({character.id})")
            
            return True, {
                "character": character.to_dict(),
                "summary": self.character_service.get_character_summary(character)
            }
        
        except Exception as e:
            session.add_error(f"Failed to create character: {e}")
            logger.error(f"Session {session_id} character creation failed: {e}")
            return False, {"error": str(e)}
    
    def get_current_step_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about the current step in the creation process."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        step_info = {
            "session_id": session_id,
            "current_step": session.current_step.value,
            "choices": session.choices.to_dict(),
            "errors": session.errors,
            "warnings": session.warnings
        }
        
        # Add step-specific information
        if session.current_step == CreationStep.TEMPLATE_SELECTION:
            step_info["available_templates"] = self.get_available_templates()
        
        elif session.current_step == CreationStep.RACE_SELECTION:
            step_info["available_races"] = [race.value for race in CharacterRace]
        
        elif session.current_step == CreationStep.CLASS_SELECTION:
            step_info["available_classes"] = [cls.value for cls in CharacterClass]
        
        elif session.current_step == CreationStep.BACKGROUND_SELECTION:
            step_info["available_backgrounds"] = [bg.value for bg in CharacterBackground]
        
        elif session.current_step == CreationStep.ABILITY_SCORES:
            step_info["ability_score_methods"] = [method.value for method in AbilityScoreMethod]
            if session.choices.ability_score_method == AbilityScoreMethod.POINT_BUY:
                step_info["point_buy_budget"] = self.character_service.POINT_BUY_BUDGET
                step_info["point_buy_costs"] = self.character_service.POINT_BUY_COSTS
        
        elif session.current_step == CreationStep.SKILLS:
            step_info["available_skills"] = self._get_available_skills_for_class(session.choices.character_class)
            step_info["required_skill_count"] = self._get_skill_choice_count(session.choices.character_class)
        
        elif session.current_step == CreationStep.EQUIPMENT:
            step_info["equipment_options"] = self._get_equipment_options_for_class(session.choices.character_class)
        
        return step_info
    
    def _get_available_skills_for_class(self, character_class: str) -> List[str]:
        """Get available skill choices for a character class."""
        class_skills = {
            "fighter": ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"],
            "wizard": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"],
            "rogue": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"],
            "cleric": ["History", "Insight", "Medicine", "Persuasion", "Religion"],
            "barbarian": ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"]
        }
        
        return class_skills.get(character_class.lower(), [])
    
    def _get_skill_choice_count(self, character_class: str) -> int:
        """Get the number of skills a character class can choose."""
        class_skill_counts = {
            "fighter": 2,
            "wizard": 2,
            "rogue": 4,
            "cleric": 2,
            "barbarian": 2
        }
        
        return class_skill_counts.get(character_class.lower(), 2)
    
    def _get_equipment_options_for_class(self, character_class: str) -> Dict[str, List[str]]:
        """Get equipment options for a character class."""
        # Simplified equipment options
        class_equipment = {
            "fighter": {
                "armor": ["Chain mail", "Leather armor + Explorers pack"],
                "weapon": ["Longsword + Shield", "Two martial weapons"],
                "ranged": ["Light crossbow + 20 bolts", "5 javelins"]
            },
            "wizard": {
                "weapon": ["Quarterstaff", "Dagger"],
                "armor": ["No armor"],
                "pack": ["Scholars pack", "Dungeoneers pack"]
            }
        }
        
        return class_equipment.get(character_class.lower(), {})
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the creation session."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session_id,
            "current_step": session.current_step.value,
            "progress": self._calculate_progress(session),
            "choices_made": self._count_choices_made(session),
            "has_errors": len(session.errors) > 0,
            "character_created": session.created_character is not None
        }
    
    def _calculate_progress(self, session: CreationSession) -> float:
        """Calculate progress percentage (0-100)."""
        step_values = {
            CreationStep.TEMPLATE_SELECTION: 10,
            CreationStep.BASIC_INFO: 20,
            CreationStep.RACE_SELECTION: 30,
            CreationStep.CLASS_SELECTION: 40,
            CreationStep.BACKGROUND_SELECTION: 50,
            CreationStep.ABILITY_SCORES: 70,
            CreationStep.SKILLS: 80,
            CreationStep.EQUIPMENT: 90,
            CreationStep.FINALIZATION: 100
        }
        
        return step_values.get(session.current_step, 0)
    
    def _count_choices_made(self, session: CreationSession) -> int:
        """Count how many choices have been made."""
        count = 0
        
        if session.choices.name:
            count += 1
        if session.choices.race:
            count += 1
        if session.choices.character_class:
            count += 1
        if session.choices.background:
            count += 1
        if session.choices.ability_scores:
            count += 1
        if session.choices.chosen_skills:
            count += 1
        
        return count


# Global service instance
creation_wizard = CharacterCreationWizard() 