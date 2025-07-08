"""Dice engine service for parsing and executing dice roll expressions."""

import re
import random
import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DiceType(Enum):
    """Standard dice types used in tabletop RPGs."""
    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D12 = 12
    D20 = 20
    D100 = 100


class RollType(Enum):
    """Types of dice rolls."""
    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"
    DROP_LOWEST = "drop_lowest"
    DROP_HIGHEST = "drop_highest"
    KEEP_HIGHEST = "keep_highest"
    KEEP_LOWEST = "keep_lowest"


@dataclass
class DiceRoll:
    """Represents a single dice roll result."""
    die_type: int  # Number of sides on the die
    result: int    # The actual roll result
    was_max: bool = False  # True if rolled maximum value
    was_min: bool = False  # True if rolled minimum value
    
    def __post_init__(self):
        self.was_max = self.result == self.die_type
        self.was_min = self.result == 1


@dataclass
class DiceGroup:
    """Represents a group of dice rolls (e.g., 3d6)."""
    count: int
    die_type: int
    modifier: int = 0
    roll_type: RollType = RollType.NORMAL
    rolls: List[DiceRoll] = field(default_factory=list)
    total: int = 0
    kept_rolls: List[DiceRoll] = field(default_factory=list)
    dropped_rolls: List[DiceRoll] = field(default_factory=list)
    
    def add_roll(self, roll: DiceRoll):
        """Add a dice roll to this group."""
        self.rolls.append(roll)
    
    def calculate_total(self):
        """Calculate the total for this dice group based on roll type."""
        if not self.rolls:
            return 0
        
        if self.roll_type == RollType.ADVANTAGE:
            # Take the highest of two rolls
            self.kept_rolls = [max(self.rolls, key=lambda r: r.result)]
            self.dropped_rolls = [r for r in self.rolls if r not in self.kept_rolls]
        elif self.roll_type == RollType.DISADVANTAGE:
            # Take the lowest of two rolls
            self.kept_rolls = [min(self.rolls, key=lambda r: r.result)]
            self.dropped_rolls = [r for r in self.rolls if r not in self.kept_rolls]
        elif self.roll_type == RollType.DROP_LOWEST and len(self.rolls) > 1:
            # Drop the lowest roll
            sorted_rolls = sorted(self.rolls, key=lambda r: r.result)
            self.dropped_rolls = [sorted_rolls[0]]
            self.kept_rolls = sorted_rolls[1:]
        elif self.roll_type == RollType.DROP_HIGHEST and len(self.rolls) > 1:
            # Drop the highest roll
            sorted_rolls = sorted(self.rolls, key=lambda r: r.result, reverse=True)
            self.dropped_rolls = [sorted_rolls[0]]
            self.kept_rolls = sorted_rolls[1:]
        else:
            # Normal roll - keep all dice
            self.kept_rolls = self.rolls.copy()
            self.dropped_rolls = []
        
        # Calculate total from kept rolls plus modifier
        dice_total = sum(roll.result for roll in self.kept_rolls)
        self.total = dice_total + self.modifier
        return self.total


@dataclass
class DiceExpression:
    """Represents a complete dice expression and its results."""
    expression: str
    dice_groups: List[DiceGroup] = field(default_factory=list)
    constant_modifier: int = 0
    total: int = 0
    seed: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    is_valid: bool = True
    error_message: Optional[str] = None
    
    def calculate_total(self):
        """Calculate the total result of the entire expression."""
        if not self.is_valid:
            return 0
        
        dice_total = sum(group.calculate_total() for group in self.dice_groups)
        self.total = dice_total + self.constant_modifier
        return self.total
    
    def get_breakdown(self) -> Dict[str, Any]:
        """Get a detailed breakdown of the roll results."""
        if not self.is_valid:
            return {
                "expression": self.expression,
                "error": self.error_message,
                "total": 0,
                "valid": False
            }
        
        breakdown = {
            "expression": self.expression,
            "total": self.total,
            "seed": self.seed,
            "timestamp": self.timestamp.isoformat(),
            "valid": True,
            "dice_groups": [],
            "constant_modifier": self.constant_modifier
        }
        
        for group in self.dice_groups:
            group_data = {
                "count": group.count,
                "die_type": f"d{group.die_type}",
                "modifier": group.modifier,
                "roll_type": group.roll_type.value,
                "total": group.total,
                "rolls": [
                    {
                        "result": roll.result,
                        "was_max": roll.was_max,
                        "was_min": roll.was_min
                    }
                    for roll in group.rolls
                ],
                "kept_rolls": [roll.result for roll in group.kept_rolls],
                "dropped_rolls": [roll.result for roll in group.dropped_rolls]
            }
            breakdown["dice_groups"].append(group_data)
        
        return breakdown


class DiceEngine:
    """Service for parsing and executing dice roll expressions."""
    
    # Regex patterns for parsing dice expressions
    DICE_PATTERN = re.compile(
        r'(?P<count>\d*)d(?P<sides>\d+)'
        r'(?P<modifier>[+-]\d+)?'
        r'(?P<roll_type>adv|dis|dl\d*|dh\d*|kh\d*|kl\d*)?',
        re.IGNORECASE
    )
    
    EXPRESSION_PATTERN = re.compile(
        r'^(?P<dice_parts>(?:\d*d\d+(?:[+-]\d+)?(?:adv|dis|dl\d*|dh\d*|kh\d*|kl\d*)?(?:\s*[+-]\s*)?)+)'
        r'(?P<constant>[+-]\d+)?$',
        re.IGNORECASE
    )
    
    VALID_DICE_TYPES = {4, 6, 8, 10, 12, 20, 100}
    
    def __init__(self):
        self.roll_history: List[DiceExpression] = []
        self.max_history_size = 1000
    
    def _create_seed(self, expression: str, custom_seed: Optional[str] = None) -> str:
        """Create a deterministic seed for the dice roll."""
        if custom_seed:
            return custom_seed
        
        # Create seed from expression + current timestamp for uniqueness
        timestamp = datetime.now().isoformat()
        seed_string = f"{expression}_{timestamp}"
        return hashlib.md5(seed_string.encode()).hexdigest()[:8]
    
    def _validate_expression(self, expression: str) -> Tuple[bool, Optional[str]]:
        """Validate that the dice expression is properly formatted."""
        # Remove whitespace
        clean_expr = re.sub(r'\s+', '', expression.strip())
        
        if not clean_expr:
            return False, "Empty expression"
        
        # Check if expression matches our pattern
        if not self.EXPRESSION_PATTERN.match(clean_expr):
            return False, "Invalid dice expression format"
        
        # Find all dice parts
        dice_matches = list(self.DICE_PATTERN.finditer(clean_expr))
        
        if not dice_matches:
            return False, "No valid dice found in expression"
        
        # Validate each dice part
        for match in dice_matches:
            sides = int(match.group('sides'))
            count = int(match.group('count') or 1)
            
            if sides not in self.VALID_DICE_TYPES:
                return False, f"Invalid die type: d{sides}. Supported: {', '.join(f'd{d}' for d in sorted(self.VALID_DICE_TYPES))}"
            
            if count <= 0 or count > 100:  # Reasonable limits
                return False, f"Invalid dice count: {count}. Must be between 1 and 100"
        
        return True, None
    
    def _parse_roll_type(self, roll_type_str: Optional[str]) -> RollType:
        """Parse the roll type modifier."""
        if not roll_type_str:
            return RollType.NORMAL
        
        roll_type_str = roll_type_str.lower()
        
        if roll_type_str == 'adv':
            return RollType.ADVANTAGE
        elif roll_type_str == 'dis':
            return RollType.DISADVANTAGE
        elif roll_type_str.startswith('dl'):
            return RollType.DROP_LOWEST
        elif roll_type_str.startswith('dh'):
            return RollType.DROP_HIGHEST
        elif roll_type_str.startswith('kh'):
            return RollType.KEEP_HIGHEST
        elif roll_type_str.startswith('kl'):
            return RollType.KEEP_LOWEST
        
        return RollType.NORMAL
    
    def _roll_die(self, sides: int, rng: random.Random) -> DiceRoll:
        """Roll a single die with the given number of sides."""
        result = rng.randint(1, sides)
        return DiceRoll(die_type=sides, result=result)
    
    def _roll_dice_group(self, count: int, sides: int, modifier: int, roll_type: RollType, rng: random.Random) -> DiceGroup:
        """Roll a group of dice (e.g., 3d6+2)."""
        group = DiceGroup(
            count=count,
            die_type=sides,
            modifier=modifier,
            roll_type=roll_type
        )
        
        # Determine how many dice to actually roll
        dice_to_roll = count
        if roll_type in [RollType.ADVANTAGE, RollType.DISADVANTAGE]:
            dice_to_roll = 2  # Always roll exactly 2 dice for advantage/disadvantage
        
        # Roll the dice
        for _ in range(dice_to_roll):
            roll = self._roll_die(sides, rng)
            group.add_roll(roll)
        
        # Calculate the total based on roll type
        group.calculate_total()
        
        return group
    
    def parse_expression(self, expression: str) -> DiceExpression:
        """Parse a dice expression string into a DiceExpression object."""
        # Validate the expression
        is_valid, error_msg = self._validate_expression(expression)
        
        if not is_valid:
            return DiceExpression(
                expression=expression,
                is_valid=False,
                error_message=error_msg
            )
        
        # Clean the expression
        clean_expr = re.sub(r'\s+', '', expression.strip())
        
        dice_expr = DiceExpression(expression=clean_expr)
        
        # Find all dice groups
        dice_matches = list(self.DICE_PATTERN.finditer(clean_expr))
        
        for match in dice_matches:
            count = int(match.group('count') or 1)
            sides = int(match.group('sides'))
            modifier = int(match.group('modifier') or 0)
            roll_type = self._parse_roll_type(match.group('roll_type'))
            
            # Create dice group (without rolling yet)
            group = DiceGroup(
                count=count,
                die_type=sides,
                modifier=modifier,
                roll_type=roll_type
            )
            dice_expr.dice_groups.append(group)
        
        # Extract constant modifier from the end of the expression
        constant_match = re.search(r'([+-]\d+)(?!d)', clean_expr)
        if constant_match:
            # Check if this modifier is not part of a dice group
            modifier_pos = constant_match.start()
            is_dice_modifier = False
            
            for match in dice_matches:
                if match.end() > modifier_pos > match.start():
                    is_dice_modifier = True
                    break
            
            if not is_dice_modifier:
                dice_expr.constant_modifier = int(constant_match.group(1))
        
        return dice_expr
    
    def execute_roll(self, expression: str, seed: Optional[str] = None) -> DiceExpression:
        """Execute a dice roll with the given expression."""
        # Parse the expression
        dice_expr = self.parse_expression(expression)
        
        if not dice_expr.is_valid:
            return dice_expr
        
        # Create and set the seed
        roll_seed = self._create_seed(expression, seed)
        dice_expr.seed = roll_seed
        
        # Create a seeded random generator for deterministic results
        rng = random.Random(roll_seed)
        
        # Execute each dice group
        for group in dice_expr.dice_groups:
            # Determine how many dice to actually roll
            dice_to_roll = group.count
            if group.roll_type in [RollType.ADVANTAGE, RollType.DISADVANTAGE]:
                dice_to_roll = 2  # Always roll exactly 2 dice for advantage/disadvantage
            
            # Roll the dice
            for _ in range(dice_to_roll):
                roll = self._roll_die(group.die_type, rng)
                group.add_roll(roll)
            
            # Calculate the total for this group
            group.calculate_total()
        
        # Calculate the final total
        dice_expr.calculate_total()
        
        # Add to history
        self._add_to_history(dice_expr)
        
        return dice_expr
    
    def _add_to_history(self, dice_expr: DiceExpression):
        """Add a dice expression to the roll history."""
        self.roll_history.append(dice_expr)
        
        # Maintain history size limit
        if len(self.roll_history) > self.max_history_size:
            self.roll_history = self.roll_history[-self.max_history_size:]
    
    def get_roll_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the recent roll history."""
        recent_rolls = self.roll_history[-limit:] if limit > 0 else self.roll_history
        return [roll.get_breakdown() for roll in reversed(recent_rolls)]
    
    def clear_history(self):
        """Clear the roll history."""
        self.roll_history.clear()
    
    def replay_roll(self, seed: str) -> Optional[DiceExpression]:
        """Replay a roll using its seed."""
        # Find the roll with the given seed
        for roll in self.roll_history:
            if roll.seed == seed:
                # Re-execute with the same seed
                return self.execute_roll(roll.expression, seed)
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about dice rolls."""
        if not self.roll_history:
            return {
                "total_rolls": 0,
                "average_result": 0,
                "most_common_expression": None,
                "critical_hits": 0,
                "critical_failures": 0
            }
        
        total_rolls = len(self.roll_history)
        total_sum = sum(roll.total for roll in self.roll_history if roll.is_valid)
        average_result = total_sum / total_rolls if total_rolls > 0 else 0
        
        # Count expression usage
        expression_counts = {}
        critical_hits = 0
        critical_failures = 0
        
        for roll in self.roll_history:
            if not roll.is_valid:
                continue
                
            # Count expressions
            expr = roll.expression
            expression_counts[expr] = expression_counts.get(expr, 0) + 1
            
            # Count critical hits/failures (nat 20s/1s on d20s)
            for group in roll.dice_groups:
                if group.die_type == 20:
                    for dice_roll in group.rolls:
                        if dice_roll.result == 20:
                            critical_hits += 1
                        elif dice_roll.result == 1:
                            critical_failures += 1
        
        most_common_expression = max(expression_counts.keys(), key=expression_counts.get) if expression_counts else None
        
        return {
            "total_rolls": total_rolls,
            "average_result": round(average_result, 2),
            "most_common_expression": most_common_expression,
            "critical_hits": critical_hits,
            "critical_failures": critical_failures,
            "expression_counts": expression_counts
        }
    
    def suggest_expressions(self, context: str = "") -> List[str]:
        """Suggest common dice expressions based on context."""
        # Common D&D dice expressions
        suggestions = [
            "1d20",      # Standard d20 roll
            "1d20+5",    # d20 with modifier
            "2d6",       # Damage roll
            "1d8+3",     # Weapon damage
            "4d6dl1",    # Ability score generation (drop lowest)
            "1d20adv",   # Advantage roll
            "1d20dis",   # Disadvantage roll
            "1d4",       # d4 roll
            "3d6",       # 3d6 roll
            "1d12+2",    # Greataxe damage
        ]
        
        # Context-specific suggestions
        context_lower = context.lower()
        
        if "attack" in context_lower:
            suggestions.insert(0, "1d20+5")  # Attack roll
            suggestions.insert(1, "1d20adv")  # Attack with advantage
        elif "damage" in context_lower:
            suggestions.insert(0, "1d8+3")   # Weapon damage
            suggestions.insert(1, "2d6")     # Spell damage
        elif "save" in context_lower or "saving" in context_lower:
            suggestions.insert(0, "1d20+3")  # Saving throw
        elif "ability" in context_lower or "stat" in context_lower:
            suggestions.insert(0, "4d6dl1")  # Ability score
        elif "initiative" in context_lower:
            suggestions.insert(0, "1d20+2")  # Initiative roll
        
        return suggestions[:10]  # Return top 10 suggestions
    
    def validate_expression_syntax(self, expression: str) -> Dict[str, Any]:
        """Validate an expression and return detailed validation info."""
        is_valid, error_msg = self._validate_expression(expression)
        
        result = {
            "valid": is_valid,
            "error": error_msg,
            "expression": expression
        }
        
        if is_valid:
            try:
                parsed = self.parse_expression(expression)
                result["parsed_groups"] = len(parsed.dice_groups)
                result["dice_types"] = [f"d{group.die_type}" for group in parsed.dice_groups]
            except Exception as e:
                result["valid"] = False
                result["error"] = f"Parse error: {str(e)}"
        
        return result


# Global dice engine instance
dice_engine = DiceEngine() 