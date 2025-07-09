"""Tool router service for detecting and routing natural language tool requests."""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools that can be detected and executed."""
    DICE_ROLL = "dice_roll"
    CHARACTER_CREATION = "character_creation"
    ENCOUNTER_GENERATION = "encounter_generation"
    KNOWLEDGE_QUERY = "knowledge_query"


@dataclass
class DetectedTool:
    """Represents a detected tool usage in a message."""
    tool_type: ToolType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    original_text: str = ""
    suggested_action: str = ""


@dataclass
class ToolResult:
    """Result of executing a detected tool."""
    tool_type: ToolType
    success: bool
    result: Any = None
    formatted_result: str = ""
    error_message: str = ""
    execution_time_ms: float = 0.0


@dataclass
class ProcessedMessage:
    """A message processed through the tool router."""
    original_message: str
    cleaned_message: str
    detected_tools: List[DetectedTool] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    has_tools: bool = False


class ToolRouter:
    """Service for detecting and routing tool usage in natural language messages."""
    
    def __init__(self, dice_engine=None, encounter_service=None):
        self.dice_engine = dice_engine
        self.encounter_service = encounter_service
        
        # Tool detection patterns with confidence weights
        self.tool_patterns = {
            ToolType.DICE_ROLL: [
                # Explicit dice expressions
                (r'\b\d*d\d+([+-]\d+)?(?:adv|dis|dl\d*|dh\d*|kh\d*|kl\d*)?\b', 0.95),
                (r'\broll\s+\d*d\d+\b', 0.9),
                (r'\b(?:roll|rolling)\s+(?:a\s+)?d\d+\b', 0.85),
                
                # D&D ability/skill checks
                (r'\b(?:strength|str|dexterity|dex|constitution|con|intelligence|int|wisdom|wis|charisma|cha)\s+(?:check|save|saving throw)\b', 0.8),
                (r'\b(?:acrobatics|athletics|deception|history|insight|intimidation|investigation|medicine|nature|perception|performance|persuasion|religion|sleight of hand|stealth|survival|arcana|animal handling)\s+check\b', 0.8),
                
                # Combat actions
                (r'\b(?:attack|hit|strike|shoot|cast|damage)\b.*\bd\d+\b', 0.75),
                (r'\battack\s+(?:roll|check)\b', 0.8),
                (r'\bdamage\s+roll\b', 0.8),
                (r'\binitiative\s+(?:roll|check)?\b', 0.8),
                
                # Death saves and other special rolls
                (r'\bdeath\s+sav(?:e|ing throw)\b', 0.9),
                (r'\bconcentration\s+(?:check|save)\b', 0.8),
                
                # General roll language
                (r'\b(?:make|do|roll|give me)\s+(?:a|an)?\s*\w*\s*(?:roll|check)\b', 0.6),
                (r'\broll\s+for\s+\w+\b', 0.7),
            ],
            
            ToolType.ENCOUNTER_GENERATION: [
                # Direct encounter requests
                (r'\b(?:generate|create|make|build|design)\s+(?:an?\s+)?encounter\b', 0.9),
                (r'\bneed\s+(?:an?\s+)?encounter\s+for\b', 0.85),
                (r'\bencounter\s+(?:for|against|with)\b', 0.8),
                
                # Difficulty specifications
                (r'\b(?:easy|medium|hard|deadly)\s+encounter\b', 0.85),
                (r'\bencounter\s+.*(?:easy|medium|hard|deadly)\b', 0.8),
                (r'\b(?:challenge rating|cr)\s+\d+\b', 0.7),
                
                # Environment specifications
                (r'\bencounter\s+in\s+(?:a|the)?\s*(?:forest|dungeon|mountains?|swamp|desert|city|urban|underground|cave|wilderness)\b', 0.8),
                (r'\b(?:forest|dungeon|mountain|swamp|desert|urban|underground)\s+encounter\b', 0.8),
                
                # Party specifications
                (r'\bfor\s+(?:a\s+)?party\s+of\s+\d+\b', 0.75),
                (r'\b(?:level|lvl)\s+\d+\s+(?:party|characters?|pcs?)\b', 0.75),
                (r'\b\d+\s+(?:level|lvl)\s+\d+\s+characters?\b', 0.8),
                
                # Monster/combat terms
                (r'\bfight\s+(?:against|with|some)\b', 0.6),
                (r'\bbattle\s+(?:against|with)\b', 0.6),
                (r'\bcombat\s+encounter\b', 0.85),
                (r'\bmonsters?\s+for\b', 0.7),
                
                # Balance/difficulty terms
                (r'\bbalanced?\s+(?:encounter|fight|combat)\b', 0.8),
                (r'\bappropriate\s+(?:encounter|challenge)\b', 0.7),
                (r'\bxp\s+budget\b', 0.9),
            ],
            
            ToolType.CHARACTER_CREATION: [
                # Character creation requests
                (r'\b(?:create|make|generate|build)\s+(?:a|an)?\s*(?:new\s+)?character\b', 0.9),
                (r'\bcharacter\s+(?:creation|generator|builder)\b', 0.9),
                (r'\bneed\s+(?:a|an)\s+(?:new\s+)?character\b', 0.8),
                
                # Class/race mentions
                (r'\bmake\s+(?:a|an)\s+(?:fighter|wizard|rogue|cleric|ranger|paladin|barbarian|bard|druid|monk|sorcerer|warlock)\b', 0.85),
                (r'\b(?:human|elf|dwarf|halfling|dragonborn|gnome|half-elf|half-orc|tiefling)\s+(?:fighter|wizard|rogue|cleric|ranger|paladin|barbarian|bard|druid|monk|sorcerer|warlock)\b', 0.9),
                
                # Ability scores
                (r'\bability\s+scores?\b', 0.7),
                (r'\b(?:point buy|standard array|roll(?:ed)?\s+stats)\b', 0.8),
                (r'\bstats?\s+(?:for|generation)\b', 0.6),
                
                # Character templates
                (r'\bcharacter\s+template\b', 0.85),
                (r'\bfrom\s+template\b', 0.8),
            ]
        }
        
        # Initialize services if available
        if self.dice_engine is None:
            try:
                from app.services.dice_engine import dice_engine
                self.dice_engine = dice_engine
            except ImportError:
                logger.warning("Dice engine not available for tool routing")
        
        if self.encounter_service is None:
            try:
                from app.services.encounter_service import encounter_service
                self.encounter_service = encounter_service
            except ImportError:
                logger.warning("Encounter service not available for tool routing")
    
    def detect_tools(self, message: str) -> List[DetectedTool]:
        """Detect potential tool usage in a message."""
        detected_tools = []
        message_lower = message.lower()
        
        for tool_type, patterns in self.tool_patterns.items():
            max_confidence = 0.0
            best_match = ""
            combined_params = {}
            
            for pattern, base_confidence in patterns:
                matches = re.finditer(pattern, message_lower, re.IGNORECASE)
                for match in matches:
                    # Adjust confidence based on context
                    confidence = self._adjust_confidence(
                        base_confidence, match.group(), message_lower, tool_type
                    )
                    
                    if confidence > max_confidence:
                        max_confidence = confidence
                        best_match = match.group()
                        
                        # Extract parameters based on tool type
                        if tool_type == ToolType.DICE_ROLL:
                            combined_params.update(self._extract_dice_parameters(match.group(), message))
                        elif tool_type == ToolType.ENCOUNTER_GENERATION:
                            combined_params.update(self._extract_encounter_parameters(message))
                        elif tool_type == ToolType.CHARACTER_CREATION:
                            combined_params.update(self._extract_character_parameters(message))
            
            # Only include tools with sufficient confidence
            if max_confidence >= 0.6:
                detected_tool = DetectedTool(
                    tool_type=tool_type,
                    confidence=max_confidence,
                    parameters=combined_params,
                    original_text=best_match,
                    suggested_action=self._generate_suggested_action(tool_type, combined_params)
                )
                detected_tools.append(detected_tool)
        
        # Sort by confidence (highest first)
        detected_tools.sort(key=lambda x: x.confidence, reverse=True)
        
        return detected_tools
    
    def _adjust_confidence(self, base_confidence: float, match_text: str, full_message: str, tool_type: ToolType) -> float:
        """Adjust confidence based on context and specificity."""
        confidence = base_confidence
        
        # Boost confidence for more specific matches
        if tool_type == ToolType.DICE_ROLL:
            if re.search(r'\bd20\b', match_text):
                confidence += 0.1  # D20 is very D&D specific
            if re.search(r'\b(?:adv|dis|advantage|disadvantage)\b', full_message):
                confidence += 0.1  # D&D 5e specific mechanics
        
        elif tool_type == ToolType.ENCOUNTER_GENERATION:
            if re.search(r'\b(?:cr|challenge rating)\s+\d+\b', full_message):
                confidence += 0.1  # Specific CR mentioned
            if re.search(r'\b(?:party|level|characters?)\b', full_message):
                confidence += 0.05  # Party context
            if re.search(r'\b(?:xp|experience)\s+(?:budget|points?)\b', full_message):
                confidence += 0.15  # Technical encounter building terms
        
        # Reduce confidence for ambiguous contexts
        if re.search(r'\b(?:not|don\'t|do not|avoid|prevent)\b.*' + re.escape(match_text), full_message):
            confidence *= 0.3  # Negative context
        
        # Boost confidence for questions
        if re.search(r'[?]', full_message):
            confidence += 0.05
        
        # Boost confidence for imperative statements
        if re.search(r'\b(?:please|can you|could you|would you)\b', full_message):
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def _extract_dice_parameters(self, match_text: str, full_message: str) -> Dict[str, Any]:
        """Extract parameters for dice rolling."""
        params = {}
        
        # Look for explicit dice expressions
        dice_match = re.search(r'(\d*)d(\d+)([+-]\d+)?(?:(adv|dis|dl\d*|dh\d*|kh\d*|kl\d*))?', match_text, re.IGNORECASE)
        if dice_match:
            params['expression'] = match_text
            params['count'] = int(dice_match.group(1)) if dice_match.group(1) else 1
            params['sides'] = int(dice_match.group(2))
            if dice_match.group(3):
                params['modifier'] = int(dice_match.group(3))
            if dice_match.group(4):
                params['roll_type'] = dice_match.group(4).lower()
        
        # Look for D&D ability checks
        ability_match = re.search(r'\b(strength|str|dexterity|dex|constitution|con|intelligence|int|wisdom|wis|charisma|cha)\s+(check|save|saving throw)\b', full_message, re.IGNORECASE)
        if ability_match:
            params['ability'] = ability_match.group(1).lower()
            params['check_type'] = ability_match.group(2).lower()
            params['suggested_expression'] = '1d20'
        
        # Look for skill checks
        skill_match = re.search(r'\b(acrobatics|athletics|deception|history|insight|intimidation|investigation|medicine|nature|perception|performance|persuasion|religion|sleight of hand|stealth|survival|arcana|animal handling)\s+check\b', full_message, re.IGNORECASE)
        if skill_match:
            params['skill'] = skill_match.group(1).lower()
            params['check_type'] = 'skill'
            params['suggested_expression'] = '1d20'
        
        return params
    
    def _extract_encounter_parameters(self, message: str) -> Dict[str, Any]:
        """Extract parameters for encounter generation."""
        params = {}
        
        # Extract difficulty
        difficulty_match = re.search(r'\b(easy|medium|hard|deadly)\b', message, re.IGNORECASE)
        if difficulty_match:
            params['difficulty'] = difficulty_match.group(1).lower()
        
        # Extract environment
        env_patterns = [
            (r'\b(?:in\s+(?:a|the)?\s*)?(forest|woods?|jungle)\b', 'forest'),
            (r'\b(?:in\s+(?:a|the)?\s*)?(dungeon|cave|underground|cavern)\b', 'dungeon'),
            (r'\b(?:in\s+(?:a|the)?\s*)?(mountain|hill)s?\b', 'mountains'),
            (r'\b(?:in\s+(?:a|the)?\s*)?(swamp|marsh|bog)\b', 'swamp'),
            (r'\b(?:in\s+(?:a|the)?\s*)?(desert)\b', 'desert'),
            (r'\b(?:in\s+(?:a|the)?\s*)?(city|town|urban|street)\b', 'urban'),
            (r'\b(?:on\s+(?:a|the)?\s*)?(coast|beach|shore)\b', 'coast'),
            (r'\b(?:in\s+(?:a|the)?\s*)?(arctic|tundra|frozen)\b', 'arctic'),
            (r'\b(?:in\s+(?:a|the)?\s*)?(grassland|plain|field)\b', 'grassland'),
        ]
        
        for pattern, env_type in env_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                params['environment'] = env_type
                break
        
        # Extract party information
        party_size_match = re.search(r'\bparty\s+of\s+(\d+)\b', message, re.IGNORECASE)
        if party_size_match:
            params['party_size'] = int(party_size_match.group(1))
        
        # Alternative party size patterns
        char_count_match = re.search(r'\b(\d+)\s+(?:characters?|pcs?|players?)\b', message, re.IGNORECASE)
        if char_count_match and 'party_size' not in params:
            params['party_size'] = int(char_count_match.group(1))
        
        # Extract party level
        level_patterns = [
            r'\b(?:level|lvl)\s+(\d+)\b',
            r'\b(\d+)(?:st|nd|rd|th)\s+level\b',
            r'\blevel\s+(\d+)\s+(?:party|characters?|pcs?)\b'
        ]
        
        for pattern in level_patterns:
            level_match = re.search(pattern, message, re.IGNORECASE)
            if level_match:
                params['party_level'] = int(level_match.group(1))
                break
        
        # Extract CR if specified
        cr_match = re.search(r'\b(?:challenge rating|cr)\s+(\d+(?:\.\d+)?|\d+/\d+)\b', message, re.IGNORECASE)
        if cr_match:
            params['target_cr'] = cr_match.group(1)
        
        return params
    
    def _extract_character_parameters(self, message: str) -> Dict[str, Any]:
        """Extract parameters for character creation."""
        params = {}
        
        # Extract race
        races = ['human', 'elf', 'dwarf', 'halfling', 'dragonborn', 'gnome', 'half-elf', 'half-orc', 'tiefling']
        for race in races:
            if re.search(rf'\b{race}\b', message, re.IGNORECASE):
                params['race'] = race
                break
        
        # Extract class
        classes = ['fighter', 'wizard', 'rogue', 'cleric', 'ranger', 'paladin', 'barbarian', 'bard', 'druid', 'monk', 'sorcerer', 'warlock']
        for char_class in classes:
            if re.search(rf'\b{char_class}\b', message, re.IGNORECASE):
                params['character_class'] = char_class
                break
        
        # Extract ability score method
        if re.search(r'\bpoint buy\b', message, re.IGNORECASE):
            params['ability_method'] = 'point_buy'
        elif re.search(r'\bstandard array\b', message, re.IGNORECASE):
            params['ability_method'] = 'standard_array'
        elif re.search(r'\broll(?:ed)?\s+stats?\b', message, re.IGNORECASE):
            params['ability_method'] = 'rolled'
        
        # Extract level
        level_match = re.search(r'\b(?:level|lvl)\s+(\d+)\b', message, re.IGNORECASE)
        if level_match:
            params['level'] = int(level_match.group(1))
        
        return params
    
    def _generate_suggested_action(self, tool_type: ToolType, params: Dict[str, Any]) -> str:
        """Generate a suggested action description for the detected tool."""
        if tool_type == ToolType.DICE_ROLL:
            if 'expression' in params:
                return f"Roll {params['expression']}"
            elif 'ability' in params:
                return f"Roll {params['ability']} {params.get('check_type', 'check')}"
            elif 'skill' in params:
                return f"Roll {params['skill']} check"
            else:
                return "Roll dice"
        
        elif tool_type == ToolType.ENCOUNTER_GENERATION:
            parts = ["Generate"]
            if 'difficulty' in params:
                parts.append(params['difficulty'])
            parts.append("encounter")
            if 'environment' in params:
                parts.append(f"in {params['environment']}")
            if 'party_size' in params and 'party_level' in params:
                parts.append(f"for {params['party_size']} level {params['party_level']} characters")
            elif 'party_size' in params:
                parts.append(f"for {params['party_size']} characters")
            elif 'party_level' in params:
                parts.append(f"for level {params['party_level']} party")
            
            return " ".join(parts)
        
        elif tool_type == ToolType.CHARACTER_CREATION:
            parts = ["Create"]
            if 'race' in params and 'character_class' in params:
                parts.append(f"{params['race']} {params['character_class']}")
            elif 'race' in params:
                parts.append(f"{params['race']} character")
            elif 'character_class' in params:
                parts.append(f"{params['character_class']} character")
            else:
                parts.append("character")
            
            if 'level' in params:
                parts.append(f"(level {params['level']})")
            
            return " ".join(parts)
        
        return f"Execute {tool_type.value}"
    
    def execute_tools(self, detected_tools: List[DetectedTool]) -> List[ToolResult]:
        """Execute detected tools and return results."""
        results = []
        
        for tool in detected_tools:
            try:
                if tool.tool_type == ToolType.DICE_ROLL:
                    result = self._execute_dice_roll(tool)
                elif tool.tool_type == ToolType.ENCOUNTER_GENERATION:
                    result = self._execute_encounter_generation(tool)
                elif tool.tool_type == ToolType.CHARACTER_CREATION:
                    result = self._execute_character_creation(tool)
                else:
                    result = ToolResult(
                        tool_type=tool.tool_type,
                        success=False,
                        error_message=f"Tool type {tool.tool_type.value} not implemented"
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error executing {tool.tool_type.value}: {e}")
                results.append(ToolResult(
                    tool_type=tool.tool_type,
                    success=False,
                    error_message=str(e)
                ))
        
        return results
    
    def _execute_dice_roll(self, tool: DetectedTool) -> ToolResult:
        """Execute a dice roll tool."""
        if not self.dice_engine:
            return ToolResult(
                tool_type=tool.tool_type,
                success=False,
                error_message="Dice engine not available"
            )
        
        try:
            params = tool.parameters
            
            # Determine what to roll
            if 'expression' in params:
                expression = params['expression']
            elif 'ability' in params or 'skill' in params:
                expression = params.get('suggested_expression', '1d20')
            else:
                expression = '1d20'  # Default
            
            # Execute the roll
            result = self.dice_engine.execute_roll(expression)
            
            # Format the result
            if 'ability' in params:
                formatted = f"{params['ability'].title()} {params.get('check_type', 'check')}: {result.total} [{expression}]"
            elif 'skill' in params:
                formatted = f"{params['skill'].title()} check: {result.total} [{expression}]"
            else:
                formatted = f"Roll: {result.total} [{expression}]"
            
            # Add breakdown if available
            if hasattr(result, 'get_breakdown'):
                breakdown = result.get_breakdown()
                if 'dice_groups' in breakdown and breakdown['dice_groups']:
                    dice_details = []
                    for group in breakdown['dice_groups']:
                        if 'kept_rolls' in group:
                            dice_results = [str(roll['result']) for roll in group['kept_rolls']]
                            dice_details.append(f"({', '.join(dice_results)})")
                    if dice_details:
                        formatted += f" Dice: {', '.join(dice_details)}"
            
            return ToolResult(
                tool_type=tool.tool_type,
                success=True,
                result=result,
                formatted_result=formatted
            )
            
        except Exception as e:
            return ToolResult(
                tool_type=tool.tool_type,
                success=False,
                error_message=f"Dice roll failed: {str(e)}"
            )
    
    def _execute_encounter_generation(self, tool: DetectedTool) -> ToolResult:
        """Execute an encounter generation tool."""
        if not self.encounter_service:
            return ToolResult(
                tool_type=tool.tool_type,
                success=False,
                error_message="Encounter service not available"
            )
        
        try:
            from app.services.encounter_service import PartyComposition, EncounterDifficulty, Environment
            
            params = tool.parameters
            
            # Set defaults
            party_size = params.get('party_size', 4)
            party_level = params.get('party_level', 5)
            difficulty = params.get('difficulty', 'medium')
            environment = params.get('environment', 'dungeon')
            
            # Convert to enums
            try:
                difficulty_enum = EncounterDifficulty(difficulty)
            except ValueError:
                difficulty_enum = EncounterDifficulty.MEDIUM
            
            try:
                environment_enum = Environment(environment)
            except ValueError:
                environment_enum = Environment.DUNGEON
            
            # Create party composition
            party_composition = PartyComposition(
                party_size=party_size,
                party_level=party_level
            )
            
            # Generate encounter
            encounter = self.encounter_service.generate_encounter(
                party_composition=party_composition,
                difficulty=difficulty_enum,
                environment=environment_enum
            )
            
            # Format the result
            monsters_text = []
            for em in encounter.monsters:
                if em.count == 1:
                    monsters_text.append(f"1 {em.monster.name}")
                else:
                    monsters_text.append(f"{em.count} {em.monster.name}s")
            
            formatted = f"**{difficulty.title()} {environment.title()} Encounter** for {party_size} level {party_level} characters:\n"
            formatted += f"• **Monsters**: {', '.join(monsters_text)}\n"
            formatted += f"• **XP**: {encounter.total_xp} total, {encounter.adjusted_xp} adjusted\n"
            
            if encounter.tactical_notes:
                formatted += f"• **Tactics**: {encounter.tactical_notes}\n"
            
            if encounter.environmental_features:
                formatted += f"• **Environment**: {', '.join(encounter.environmental_features[:2])}"
            
            return ToolResult(
                tool_type=tool.tool_type,
                success=True,
                result=encounter,
                formatted_result=formatted
            )
            
        except Exception as e:
            return ToolResult(
                tool_type=tool.tool_type,
                success=False,
                error_message=f"Encounter generation failed: {str(e)}"
            )
    
    def _execute_character_creation(self, tool: DetectedTool) -> ToolResult:
        """Execute a character creation tool."""
        try:
            params = tool.parameters
            
            # For now, return a formatted suggestion
            # TODO: Integrate with character service when available
            
            race = params.get('race', 'human').title()
            char_class = params.get('character_class', 'fighter').title()
            level = params.get('level', 1)
            
            formatted = f"**Character Creation Suggestion**:\n"
            formatted += f"• **Race**: {race}\n"
            formatted += f"• **Class**: {char_class}\n"
            formatted += f"• **Level**: {level}\n"
            
            if 'ability_method' in params:
                formatted += f"• **Ability Scores**: {params['ability_method'].replace('_', ' ').title()}\n"
            
            formatted += "\nUse the character creation wizard API endpoints to create this character."
            
            return ToolResult(
                tool_type=tool.tool_type,
                success=True,
                result=params,
                formatted_result=formatted
            )
            
        except Exception as e:
            return ToolResult(
                tool_type=tool.tool_type,
                success=False,
                error_message=f"Character creation failed: {str(e)}"
            )
    
    def process_message(self, message: str, execute_tools: bool = True) -> ProcessedMessage:
        """Process a message through the complete tool detection and execution pipeline."""
        # Detect tools
        detected_tools = self.detect_tools(message)
        
        # Calculate confidence scores
        confidence_scores = {
            tool.tool_type.value: tool.confidence 
            for tool in detected_tools
        }
        
        # Execute tools if requested
        tool_results = []
        if execute_tools and detected_tools:
            tool_results = self.execute_tools(detected_tools)
        
        # Clean the message (remove tool-specific text for LLM processing)
        cleaned_message = self._clean_message_for_llm(message, detected_tools)
        
        return ProcessedMessage(
            original_message=message,
            cleaned_message=cleaned_message,
            detected_tools=detected_tools,
            tool_results=tool_results,
            confidence_scores=confidence_scores,
            has_tools=len(detected_tools) > 0
        )
    
    def _clean_message_for_llm(self, message: str, detected_tools: List[DetectedTool]) -> str:
        """Clean the message by removing or replacing tool-specific expressions."""
        cleaned = message
        
        # For now, keep the original message intact
        # Future enhancement: replace dice expressions with results, etc.
        
        return cleaned


# Global tool router instance
tool_router = ToolRouter() 