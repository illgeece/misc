"""Tool router service for detecting and routing tool usage in chat messages."""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum

from .dice_engine import DiceEngine, DiceExpression

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools that can be detected and routed."""
    DICE_ROLL = "dice_roll"
    FILE_QUERY = "file_query"
    CHARACTER_CREATE = "character_create"
    KNOWLEDGE_SEARCH = "knowledge_search"
    SPELL_LOOKUP = "spell_lookup"
    MONSTER_LOOKUP = "monster_lookup"
    RULE_LOOKUP = "rule_lookup"


@dataclass
class ToolDetection:
    """Represents a detected tool usage in a message."""
    tool_type: ToolType
    confidence: float  # 0.0 to 1.0
    extracted_text: str  # The specific text that triggered the detection
    parameters: Dict[str, Any]  # Tool-specific parameters
    start_pos: int = 0  # Position in original message
    end_pos: int = 0    # End position in original message


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool_type: ToolType
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None


@dataclass
class MessageWithTools:
    """A chat message with detected and executed tools."""
    original_message: str
    cleaned_message: str  # Message with tool expressions removed/replaced
    detected_tools: List[ToolDetection]
    tool_results: List[ToolResult]
    has_tools: bool = False


class ToolRouter:
    """Service for detecting and routing tool usage in chat messages."""
    
    # Dice roll detection patterns
    DICE_PATTERNS = [
        # Direct dice expressions
        re.compile(r'\b(\d*d\d+(?:[+-]\d+)?(?:adv|dis|dl\d*|dh\d*|kh\d*|kl\d*)?)\b', re.IGNORECASE),
        
        # Natural language dice requests
        re.compile(r'\b(?:roll|make|do)\s+(?:a\s+)?(\d*d\d+(?:[+-]\d+)?)\b', re.IGNORECASE),
        re.compile(r'\b(?:roll|throw)\s+(?:a\s+|an\s+)?(\d+)\s*(?:sided\s+)?(?:die|dice)\b', re.IGNORECASE),
        re.compile(r'\b(?:d|dice?)\s*(\d+)\s*(?:roll|check)?\b', re.IGNORECASE),
        
        # D&D specific rolls
        re.compile(r'\b(?:attack|hit|strike)(?:\s+with)?\s+(\d*d\d+(?:[+-]\d+)?)\b', re.IGNORECASE),
        re.compile(r'\b(?:damage|dmg)(?:\s+of)?\s+(\d*d\d+(?:[+-]\d+)?)\b', re.IGNORECASE),
        re.compile(r'\b(\d*d\d+(?:[+-]\d+)?)\s+(?:damage|dmg)\b', re.IGNORECASE),
        
        # Saving throws and checks
        re.compile(r'\b(?:saving?\s+throw|save|check)\s+(\d*d\d+(?:[+-]\d+)?|\d+)?\b', re.IGNORECASE),
        re.compile(r'\b(?:make\s+a|roll\s+a|do\s+a)\s+(\w+)\s+(?:check|save|saving\s+throw)\b', re.IGNORECASE),
        
        # Initiative and specific D&D mechanics
        re.compile(r'\b(?:initiative|init)(?:\s+roll)?\b', re.IGNORECASE),
        re.compile(r'\b(?:advantage|adv|disadvantage|dis|with\s+advantage|with\s+disadvantage)\b', re.IGNORECASE),
    ]
    
    # Common ability/skill names for auto-suggesting d20 rolls
    D20_ABILITIES = {
        'strength', 'str', 'dexterity', 'dex', 'constitution', 'con',
        'intelligence', 'int', 'wisdom', 'wis', 'charisma', 'cha',
        'acrobatics', 'animal handling', 'arcana', 'athletics', 'deception',
        'history', 'insight', 'intimidation', 'investigation', 'medicine',
        'nature', 'perception', 'performance', 'persuasion', 'religion',
        'sleight of hand', 'stealth', 'survival', 'initiative'
    }
    
    # File query patterns
    FILE_QUERY_PATTERNS = [
        re.compile(r'\b(?:show|display|get|find|lookup?)\s+(?:file|document|character|pc)\s+([^\s]+)\b', re.IGNORECASE),
        re.compile(r'\b(?:what|show)(?:\s+is|\s+are)?\s+(?:in\s+)?([^\s]+\.(?:pdf|md|yaml|yml|json))\b', re.IGNORECASE),
        re.compile(r'\b(?:open|read|view)\s+([^\s]+)\b', re.IGNORECASE),
    ]
    
    # Knowledge search patterns
    KNOWLEDGE_PATTERNS = [
        re.compile(r'\b(?:what\s+(?:is|are)|tell\s+me\s+about|explain|describe)\s+(.+?)(?:\?|$)', re.IGNORECASE),
        re.compile(r'\b(?:how\s+(?:does|do|to)|where\s+(?:is|are))\s+(.+?)(?:\?|$)', re.IGNORECASE),
        re.compile(r'\b(?:search|find|lookup?)\s+(?:for\s+)?(.+?)\b', re.IGNORECASE),
    ]
    
    def __init__(self, dice_engine: Optional[DiceEngine] = None):
        self.dice_engine = dice_engine or DiceEngine()
        
        # Confidence thresholds for different tool types
        self.confidence_thresholds = {
            ToolType.DICE_ROLL: 0.6,
            ToolType.FILE_QUERY: 0.7,
            ToolType.KNOWLEDGE_SEARCH: 0.5,
        }
    
    def detect_tools(self, message: str) -> List[ToolDetection]:
        """Detect all potential tool usages in a message."""
        detections = []
        
        # Detect dice rolls
        detections.extend(self._detect_dice_rolls(message))
        
        # Detect file queries
        detections.extend(self._detect_file_queries(message))
        
        # Detect knowledge searches
        detections.extend(self._detect_knowledge_searches(message))
        
        # Sort by position in message
        detections.sort(key=lambda d: d.start_pos)
        
        # Filter by confidence threshold
        filtered_detections = []
        for detection in detections:
            threshold = self.confidence_thresholds.get(detection.tool_type, 0.5)
            if detection.confidence >= threshold:
                filtered_detections.append(detection)
        
        return filtered_detections
    
    def _detect_dice_rolls(self, message: str) -> List[ToolDetection]:
        """Detect dice roll expressions in a message."""
        detections = []
        message_lower = message.lower()
        
        # Check for direct dice expressions
        for pattern in self.DICE_PATTERNS:
            for match in pattern.finditer(message):
                dice_expr = match.group(1) if match.groups() else match.group(0)
                
                # Validate the dice expression
                if self._is_valid_dice_expression(dice_expr):
                    confidence = self._calculate_dice_confidence(match.group(0), message_lower)
                    
                    detection = ToolDetection(
                        tool_type=ToolType.DICE_ROLL,
                        confidence=confidence,
                        extracted_text=match.group(0),
                        parameters={'expression': dice_expr},
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    detections.append(detection)
        
        # Check for ability/skill checks that should use d20
        for ability in self.D20_ABILITIES:
            ability_patterns = [
                re.compile(rf'\b{re.escape(ability)}\s+(?:check|save|saving\s+throw|roll)\b', re.IGNORECASE),
                re.compile(rf'\b(?:make\s+a|roll\s+a|do\s+a)\s+{re.escape(ability)}(?:\s+check)?\b', re.IGNORECASE),
            ]
            
            for pattern in ability_patterns:
                for match in pattern.finditer(message):
                    detection = ToolDetection(
                        tool_type=ToolType.DICE_ROLL,
                        confidence=0.8,
                        extracted_text=match.group(0),
                        parameters={
                            'expression': '1d20',
                            'suggested': True,
                            'ability': ability,
                            'check_type': 'ability_check'
                        },
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    detections.append(detection)
        
        # Special case for initiative
        initiative_pattern = re.compile(r'\b(?:initiative|init)(?:\s+roll)?\b', re.IGNORECASE)
        for match in initiative_pattern.finditer(message):
            detection = ToolDetection(
                tool_type=ToolType.DICE_ROLL,
                confidence=0.9,
                extracted_text=match.group(0),
                parameters={
                    'expression': '1d20',
                    'suggested': True,
                    'check_type': 'initiative'
                },
                start_pos=match.start(),
                end_pos=match.end()
            )
            detections.append(detection)
        
        return detections
    
    def _detect_file_queries(self, message: str) -> List[ToolDetection]:
        """Detect file query requests in a message."""
        detections = []
        
        for pattern in self.FILE_QUERY_PATTERNS:
            for match in pattern.finditer(message):
                file_reference = match.group(1) if match.groups() else match.group(0)
                confidence = 0.8 if any(ext in file_reference.lower() for ext in ['.pdf', '.md', '.yaml', '.yml', '.json']) else 0.7
                
                detection = ToolDetection(
                    tool_type=ToolType.FILE_QUERY,
                    confidence=confidence,
                    extracted_text=match.group(0),
                    parameters={'file_reference': file_reference},
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                detections.append(detection)
        
        return detections
    
    def _detect_knowledge_searches(self, message: str) -> List[ToolDetection]:
        """Detect knowledge search requests in a message."""
        detections = []
        
        for pattern in self.KNOWLEDGE_PATTERNS:
            for match in pattern.finditer(message):
                search_query = match.group(1) if match.groups() else match.group(0)
                search_query = search_query.strip()
                
                # Skip very short or generic queries
                if len(search_query) < 3 or search_query.lower() in ['it', 'that', 'this', 'what', 'how']:
                    continue
                
                confidence = self._calculate_knowledge_confidence(search_query, message)
                
                detection = ToolDetection(
                    tool_type=ToolType.KNOWLEDGE_SEARCH,
                    confidence=confidence,
                    extracted_text=match.group(0),
                    parameters={'query': search_query},
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                detections.append(detection)
        
        return detections
    
    def _is_valid_dice_expression(self, expr: str) -> bool:
        """Check if a string is a valid dice expression."""
        if not expr:
            return False
        
        try:
            result = self.dice_engine.validate_expression_syntax(expr)
            return result['valid']
        except Exception:
            return False
    
    def _calculate_dice_confidence(self, matched_text: str, message_lower: str) -> float:
        """Calculate confidence score for dice roll detection."""
        confidence = 0.5
        matched_lower = matched_text.lower()
        
        # Higher confidence for explicit dice patterns
        if re.search(r'\d*d\d+', matched_lower):
            confidence += 0.3
        
        # Context clues that increase confidence
        dice_context_words = ['roll', 'dice', 'check', 'save', 'attack', 'damage', 'hit', 'throw']
        for word in dice_context_words:
            if word in message_lower:
                confidence += 0.1
                break
        
        # RPG-specific context
        rpg_words = ['initiative', 'saving throw', 'ability check', 'advantage', 'disadvantage']
        for phrase in rpg_words:
            if phrase in message_lower:
                confidence += 0.2
                break
        
        return min(confidence, 1.0)
    
    def _calculate_knowledge_confidence(self, query: str, message: str) -> float:
        """Calculate confidence score for knowledge search detection."""
        confidence = 0.4
        
        # Longer queries are more likely to be knowledge searches
        if len(query) > 10:
            confidence += 0.2
        
        # RPG/D&D terms increase confidence
        rpg_terms = [
            'spell', 'magic', 'monster', 'creature', 'class', 'race', 'feat',
            'ability', 'skill', 'armor', 'weapon', 'item', 'rule', 'mechanic',
            'combat', 'dungeon', 'adventure', 'character', 'npc', 'campaign'
        ]
        
        query_lower = query.lower()
        message_lower = message.lower()
        
        for term in rpg_terms:
            if term in query_lower or term in message_lower:
                confidence += 0.1
        
        # Question words indicate knowledge requests
        question_words = ['what', 'how', 'where', 'when', 'why', 'who']
        for word in question_words:
            if word in message_lower:
                confidence += 0.1
                break
        
        return min(confidence, 1.0)
    
    def execute_tool(self, detection: ToolDetection) -> ToolResult:
        """Execute a detected tool and return the result."""
        start_time = None
        try:
            import time
            start_time = time.time()
            
            if detection.tool_type == ToolType.DICE_ROLL:
                return self._execute_dice_roll(detection)
            elif detection.tool_type == ToolType.FILE_QUERY:
                return self._execute_file_query(detection)
            elif detection.tool_type == ToolType.KNOWLEDGE_SEARCH:
                return self._execute_knowledge_search(detection)
            else:
                return ToolResult(
                    tool_type=detection.tool_type,
                    success=False,
                    result=None,
                    error_message=f"Tool type {detection.tool_type} not implemented"
                )
        
        except Exception as e:
            logger.error(f"Error executing tool {detection.tool_type}: {str(e)}")
            return ToolResult(
                tool_type=detection.tool_type,
                success=False,
                result=None,
                error_message=str(e)
            )
        
        finally:
            if start_time:
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    def _execute_dice_roll(self, detection: ToolDetection) -> ToolResult:
        """Execute a dice roll tool."""
        expression = detection.parameters.get('expression', '1d20')
        
        try:
            result = self.dice_engine.execute_roll(expression)
            
            return ToolResult(
                tool_type=ToolType.DICE_ROLL,
                success=result.is_valid,
                result=result.get_breakdown(),
                error_message=result.error_message if not result.is_valid else None
            )
        
        except Exception as e:
            return ToolResult(
                tool_type=ToolType.DICE_ROLL,
                success=False,
                result=None,
                error_message=f"Dice roll failed: {str(e)}"
            )
    
    def _execute_file_query(self, detection: ToolDetection) -> ToolResult:
        """Execute a file query tool."""
        # Placeholder - would integrate with file system service
        file_reference = detection.parameters.get('file_reference', '')
        
        return ToolResult(
            tool_type=ToolType.FILE_QUERY,
            success=False,
            result=None,
            error_message="File query not implemented yet"
        )
    
    def _execute_knowledge_search(self, detection: ToolDetection) -> ToolResult:
        """Execute a knowledge search tool."""
        # Placeholder - would integrate with knowledge service
        query = detection.parameters.get('query', '')
        
        return ToolResult(
            tool_type=ToolType.KNOWLEDGE_SEARCH,
            success=False,
            result=None,
            error_message="Knowledge search not implemented yet"
        )
    
    def process_message(self, message: str, execute_tools: bool = True) -> MessageWithTools:
        """Process a message, detect tools, and optionally execute them."""
        # Detect all tools in the message
        detections = self.detect_tools(message)
        
        # Initialize result
        result = MessageWithTools(
            original_message=message,
            cleaned_message=message,
            detected_tools=detections,
            tool_results=[],
            has_tools=len(detections) > 0
        )
        
        if execute_tools and detections:
            # Execute each detected tool
            for detection in detections:
                tool_result = self.execute_tool(detection)
                result.tool_results.append(tool_result)
            
            # Clean the message by replacing tool expressions with results
            result.cleaned_message = self._clean_message_with_results(message, detections, result.tool_results)
        
        return result
    
    def _clean_message_with_results(self, message: str, detections: List[ToolDetection], results: List[ToolResult]) -> str:
        """Clean the message by replacing tool expressions with their results."""
        cleaned = message
        
        # Process replacements from end to start to maintain string positions
        for detection, result in reversed(list(zip(detections, results))):
            if result.success and detection.tool_type == ToolType.DICE_ROLL:
                # Replace dice expression with result
                breakdown = result.result
                total = breakdown.get('total', 0)
                expression = breakdown.get('expression', '')
                
                replacement = f"**{expression}** → **{total}**"
                
                # Add critical hit/failure indicators
                if any(group.get('die_type') == 'd20' for group in breakdown.get('dice_groups', [])):
                    for group in breakdown.get('dice_groups', []):
                        if group.get('die_type') == 'd20':
                            for roll in group.get('rolls', []):
                                if roll.get('result') == 20:
                                    replacement += " 🎯"  # Critical hit
                                elif roll.get('result') == 1:
                                    replacement += " 💥"  # Critical failure
                
                cleaned = cleaned[:detection.start_pos] + replacement + cleaned[detection.end_pos:]
            
            elif not result.success:
                # Mark failed tool executions
                cleaned = cleaned[:detection.start_pos] + f"~~{detection.extracted_text}~~ ❌" + cleaned[detection.end_pos:]
        
        return cleaned
    
    def get_tool_suggestions(self, message: str) -> List[Dict[str, Any]]:
        """Get tool suggestions based on message content."""
        suggestions = []
        
        detections = self.detect_tools(message)
        
        for detection in detections:
            if detection.tool_type == ToolType.DICE_ROLL:
                expression = detection.parameters.get('expression', '1d20')
                suggestions.append({
                    'type': 'dice_roll',
                    'expression': expression,
                    'description': f"Roll {expression}",
                    'confidence': detection.confidence
                })
            
            elif detection.tool_type == ToolType.KNOWLEDGE_SEARCH:
                query = detection.parameters.get('query', '')
                suggestions.append({
                    'type': 'knowledge_search',
                    'query': query,
                    'description': f"Search for: {query}",
                    'confidence': detection.confidence
                })
        
        return suggestions


# Global tool router instance
tool_router = ToolRouter() 