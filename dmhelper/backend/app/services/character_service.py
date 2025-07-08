"""Character service for D&D 5e character creation, management, and validation."""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AbilityScore(Enum):
    """D&D 5e ability scores."""
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"


class CharacterClass(Enum):
    """D&D 5e character classes."""
    BARBARIAN = "barbarian"
    BARD = "bard"
    CLERIC = "cleric"
    DRUID = "druid"
    FIGHTER = "fighter"
    MONK = "monk"
    PALADIN = "paladin"
    RANGER = "ranger"
    ROGUE = "rogue"
    SORCERER = "sorcerer"
    WARLOCK = "warlock"
    WIZARD = "wizard"


class CharacterRace(Enum):
    """D&D 5e character races."""
    DRAGONBORN = "dragonborn"
    DWARF = "dwarf"
    ELF = "elf"
    GNOME = "gnome"
    HALF_ELF = "half-elf"
    HALFLING = "halfling"
    HALF_ORC = "half-orc"
    HUMAN = "human"
    TIEFLING = "tiefling"


class CharacterBackground(Enum):
    """D&D 5e character backgrounds."""
    ACOLYTE = "acolyte"
    CRIMINAL = "criminal"
    FOLK_HERO = "folk_hero"
    NOBLE = "noble"
    SAGE = "sage"
    SOLDIER = "soldier"
    CHARLATAN = "charlatan"
    ENTERTAINER = "entertainer"
    GUILD_ARTISAN = "guild_artisan"
    HERMIT = "hermit"
    OUTLANDER = "outlander"
    SAILOR = "sailor"


class AbilityScoreMethod(Enum):
    """Methods for generating ability scores."""
    STANDARD_ARRAY = "standard_array"  # 15, 14, 13, 12, 10, 8
    POINT_BUY = "point_buy"           # 27 points to distribute
    ROLL_4D6_DROP_LOWEST = "4d6dl1"  # Roll 4d6, drop lowest
    ROLL_3D6 = "3d6"                 # Straight 3d6 rolls
    MANUAL = "manual"                 # Manually set values
    
    # Alias for backwards compatibility
    ROLLED = ROLL_4D6_DROP_LOWEST


@dataclass
class AbilityScores:
    """Character ability scores with modifiers."""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    def get_modifier(self, ability: str) -> int:
        """Calculate ability modifier."""
        score = getattr(self, ability.lower())
        return (score - 10) // 2
    
    def get_all_modifiers(self) -> Dict[str, int]:
        """Get all ability modifiers."""
        return {
            ability.value: self.get_modifier(ability.value)
            for ability in AbilityScore
        }
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EquipmentItem:
    """Character equipment item."""
    name: str
    item_type: str
    description: str = ""
    quantity: int = 1
    weight: float = 0.0
    value_gp: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Combat properties (for weapons/armor)
    damage: Optional[str] = None
    damage_type: Optional[str] = None
    armor_class: Optional[int] = None
    ac_bonus: Optional[int] = None
    range_normal: Optional[int] = None
    range_long: Optional[int] = None


@dataclass
class CharacterFeature:
    """Character class/race/background feature."""
    name: str
    description: str
    source: str  # "class", "race", "background", "feat"
    level_acquired: int = 1
    uses_per_rest: Optional[int] = None
    rest_type: Optional[str] = None  # "short", "long"


@dataclass
class Character:
    """Complete D&D 5e character representation."""
    # Basic info
    id: str
    name: str
    race: str
    character_class: str
    background: str
    level: int = 1
    
    # Core stats
    ability_scores: AbilityScores = field(default_factory=AbilityScores)
    hit_points: int = 0
    max_hit_points: int = 0
    armor_class: int = 10
    speed: int = 30
    proficiency_bonus: int = 2
    
    # Skills and proficiencies
    skill_proficiencies: List[str] = field(default_factory=list)
    saving_throw_proficiencies: List[str] = field(default_factory=list)
    armor_proficiencies: List[str] = field(default_factory=list)
    weapon_proficiencies: List[str] = field(default_factory=list)
    tool_proficiencies: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    
    # Equipment and features
    equipment: List[EquipmentItem] = field(default_factory=list)
    features: List[CharacterFeature] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""
    
    def update_timestamp(self):
        """Update the last modified timestamp."""
        self.updated_at = datetime.now().isoformat()
    
    def get_ability_modifier(self, ability: str) -> int:
        """Get ability score modifier."""
        return self.ability_scores.get_modifier(ability)
    
    def get_skill_modifier(self, skill: str) -> int:
        """Calculate skill modifier including proficiency."""
        skill_to_ability = {
            "acrobatics": "dexterity",
            "animal_handling": "wisdom",
            "arcana": "intelligence",
            "athletics": "strength",
            "deception": "charisma",
            "history": "intelligence",
            "insight": "wisdom",
            "intimidation": "charisma",
            "investigation": "intelligence",
            "medicine": "wisdom",
            "nature": "intelligence",
            "perception": "wisdom",
            "performance": "charisma",
            "persuasion": "charisma",
            "religion": "intelligence",
            "sleight_of_hand": "dexterity",
            "stealth": "dexterity",
            "survival": "wisdom"
        }
        
        ability = skill_to_ability.get(skill.lower().replace(" ", "_"))
        if not ability:
            return 0
        
        modifier = self.get_ability_modifier(ability)
        
        # Add proficiency bonus if proficient
        if skill in self.skill_proficiencies:
            modifier += self.proficiency_bonus
        
        return modifier
    
    def get_saving_throw_modifier(self, ability: str) -> int:
        """Calculate saving throw modifier including proficiency."""
        modifier = self.get_ability_modifier(ability)
        
        # Add proficiency bonus if proficient
        if ability in self.saving_throw_proficiencies:
            modifier += self.proficiency_bonus
        
        return modifier
    
    def calculate_armor_class(self) -> int:
        """Calculate total armor class from equipment and abilities."""
        base_ac = 10 + self.get_ability_modifier("dexterity")
        
        # Find armor
        armor_ac = 0
        armor_dex_mod = 999  # Max dex modifier allowed by armor
        
        for item in self.equipment:
            if item.item_type == "armor" and item.armor_class:
                armor_ac = item.armor_class
                # Heavy armor typically doesn't add dex, medium armor caps at +2
                if "heavy" in item.name.lower():
                    armor_dex_mod = 0
                elif "medium" in item.name.lower():
                    armor_dex_mod = 2
                break
        
        if armor_ac > 0:
            dex_mod = min(self.get_ability_modifier("dexterity"), armor_dex_mod)
            base_ac = armor_ac + max(0, dex_mod)
        
        # Add shield bonus
        for item in self.equipment:
            if item.item_type == "shield" and item.ac_bonus:
                base_ac += item.ac_bonus
        
        return base_ac
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "race": self.race,
            "character_class": self.character_class,
            "background": self.background,
            "level": self.level,
            "ability_scores": self.ability_scores.to_dict(),
            "hit_points": self.hit_points,
            "max_hit_points": self.max_hit_points,
            "armor_class": self.armor_class,
            "speed": self.speed,
            "proficiency_bonus": self.proficiency_bonus,
            "skill_proficiencies": self.skill_proficiencies,
            "saving_throw_proficiencies": self.saving_throw_proficiencies,
            "armor_proficiencies": self.armor_proficiencies,
            "weapon_proficiencies": self.weapon_proficiencies,
            "tool_proficiencies": self.tool_proficiencies,
            "languages": self.languages,
            "equipment": [asdict(item) for item in self.equipment],
            "features": [asdict(feature) for feature in self.features],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "notes": self.notes
        }


class CharacterService:
    """Service for managing D&D 5e characters."""
    
    # D&D 5e Constants
    STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
    POINT_BUY_BUDGET = 27
    POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    
    # Proficiency bonus by level
    PROFICIENCY_BONUS_BY_LEVEL = {
        1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3,
        9: 4, 10: 4, 11: 4, 12: 4, 13: 5, 14: 5, 15: 5,
        16: 5, 17: 6, 18: 6, 19: 6, 20: 6
    }
    
    # Hit dice by class
    HIT_DICE_BY_CLASS = {
        CharacterClass.BARBARIAN: 12,
        CharacterClass.FIGHTER: 10,
        CharacterClass.PALADIN: 10,
        CharacterClass.RANGER: 10,
        CharacterClass.BARD: 8,
        CharacterClass.CLERIC: 8,
        CharacterClass.DRUID: 8,
        CharacterClass.MONK: 8,
        CharacterClass.ROGUE: 8,
        CharacterClass.WARLOCK: 8,
        CharacterClass.SORCERER: 6,
        CharacterClass.WIZARD: 6
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.characters_dir = Path(self.settings.campaign_root) / "characters" / "pcs"
        self.templates_dir = Path(self.settings.campaign_root) / "characters" / "templates"
        
        # Ensure directories exist
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._character_cache: Dict[str, Character] = {}
    
    def generate_ability_scores(self, method: AbilityScoreMethod, custom_values: Optional[List[int]] = None) -> AbilityScores:
        """Generate ability scores using the specified method."""
        if method == AbilityScoreMethod.STANDARD_ARRAY:
            # User will assign these values to abilities
            scores = self.STANDARD_ARRAY.copy()
            return AbilityScores(
                strength=scores[0], dexterity=scores[1], constitution=scores[2],
                intelligence=scores[3], wisdom=scores[4], charisma=scores[5]
            )
        
        elif method == AbilityScoreMethod.MANUAL and custom_values:
            if len(custom_values) != 6:
                raise ValueError("Must provide exactly 6 ability scores")
            
            return AbilityScores(
                strength=custom_values[0], dexterity=custom_values[1], constitution=custom_values[2],
                intelligence=custom_values[3], wisdom=custom_values[4], charisma=custom_values[5]
            )
        
        elif method == AbilityScoreMethod.POINT_BUY:
            # Start with 8s and let user distribute points
            return AbilityScores(
                strength=8, dexterity=8, constitution=8,
                intelligence=8, wisdom=8, charisma=8
            )
        
        else:
            # For dice-based methods, we'll use the dice engine
            # This will be integrated with M3's DiceEngine
            from app.services.dice_engine import dice_engine
            
            scores = []
            if method == AbilityScoreMethod.ROLL_4D6_DROP_LOWEST:
                for _ in range(6):
                    result = dice_engine.execute_roll("4d6dl1")
                    scores.append(result.total)
            elif method == AbilityScoreMethod.ROLL_3D6:
                for _ in range(6):
                    result = dice_engine.execute_roll("3d6")
                    scores.append(result.total)
            
            return AbilityScores(
                strength=scores[0], dexterity=scores[1], constitution=scores[2],
                intelligence=scores[3], wisdom=scores[4], charisma=scores[5]
            )
    
    def validate_point_buy(self, ability_scores: AbilityScores) -> Tuple[bool, str]:
        """Validate that ability scores follow point buy rules."""
        scores = [
            ability_scores.strength, ability_scores.dexterity, ability_scores.constitution,
            ability_scores.intelligence, ability_scores.wisdom, ability_scores.charisma
        ]
        
        # Check score ranges
        if any(score < 8 or score > 15 for score in scores):
            return False, "Point buy scores must be between 8 and 15"
        
        # Calculate total cost
        total_cost = sum(self.POINT_BUY_COSTS.get(score, 999) for score in scores)
        
        if total_cost > self.POINT_BUY_BUDGET:
            return False, f"Point buy cost ({total_cost}) exceeds budget ({self.POINT_BUY_BUDGET})"
        
        return True, ""
    
    def create_character(
        self,
        name: str,
        race: str,
        character_class: str,
        background: str,
        ability_scores: AbilityScores,
        ability_score_method: AbilityScoreMethod = AbilityScoreMethod.STANDARD_ARRAY
    ) -> Character:
        """Create a new character with calculated stats."""
        
        # Validate ability scores if using point buy
        if ability_score_method == AbilityScoreMethod.POINT_BUY:
            valid, error = self.validate_point_buy(ability_scores)
            if not valid:
                raise ValueError(f"Invalid point buy: {error}")
        
        # Create character
        character = Character(
            id=str(uuid.uuid4()),
            name=name,
            race=race,
            character_class=character_class,
            background=background,
            ability_scores=ability_scores
        )
        
        # Apply racial bonuses
        self._apply_racial_bonuses(character)
        
        # Calculate derived stats
        self._calculate_derived_stats(character)
        
        # Add class features
        self._add_class_features(character)
        
        # Add background features
        self._add_background_features(character)
        
        # Add starting equipment
        self._add_starting_equipment(character)
        
        # Recalculate AC after equipment
        character.armor_class = character.calculate_armor_class()
        
        # Cache and save
        self._character_cache[character.id] = character
        self.save_character(character)
        
        return character
    
    def _apply_racial_bonuses(self, character: Character):
        """Apply racial ability score bonuses and features."""
        race = character.race.lower()
        
        # Simplified racial bonuses - in a full implementation, this would be more comprehensive
        racial_bonuses = {
            "human": {"strength": 1, "dexterity": 1, "constitution": 1, "intelligence": 1, "wisdom": 1, "charisma": 1},
            "elf": {"dexterity": 2},
            "dwarf": {"constitution": 2},
            "halfling": {"dexterity": 2},
            "dragonborn": {"strength": 2, "charisma": 1},
            "gnome": {"intelligence": 2},
            "half-elf": {"charisma": 2, "strength": 1, "dexterity": 1},  # Simplified
            "half-orc": {"strength": 2, "constitution": 1},
            "tiefling": {"intelligence": 1, "charisma": 2}
        }
        
        bonuses = racial_bonuses.get(race, {})
        for ability, bonus in bonuses.items():
            current = getattr(character.ability_scores, ability)
            setattr(character.ability_scores, ability, current + bonus)
        
        # Add racial features (simplified)
        if race == "human":
            character.features.append(CharacterFeature(
                name="Extra Language",
                description="You can speak, read, and write one extra language of your choice.",
                source="race"
            ))
            character.features.append(CharacterFeature(
                name="Extra Skill",
                description="You gain proficiency in one skill of your choice.",
                source="race"
            ))
        elif race == "elf":
            character.features.append(CharacterFeature(
                name="Darkvision",
                description="You can see in dim light within 60 feet as if it were bright light.",
                source="race"
            ))
            character.skill_proficiencies.append("Perception")
        elif race == "dwarf":
            character.features.append(CharacterFeature(
                name="Darkvision",
                description="You can see in dim light within 60 feet as if it were bright light.",
                source="race"
            ))
            character.features.append(CharacterFeature(
                name="Dwarven Resilience",
                description="You have advantage on saving throws against poison.",
                source="race"
            ))
    
    def _calculate_derived_stats(self, character: Character):
        """Calculate hit points, proficiency bonus, and other derived stats."""
        # Proficiency bonus
        character.proficiency_bonus = self.PROFICIENCY_BONUS_BY_LEVEL.get(character.level, 2)
        
        # Hit points
        class_enum = None
        try:
            class_enum = CharacterClass(character.character_class.lower())
        except ValueError:
            class_enum = CharacterClass.FIGHTER  # Default
        
        hit_die = self.HIT_DICE_BY_CLASS.get(class_enum, 8)
        con_modifier = character.get_ability_modifier("constitution")
        
        # At level 1, you get max hit die + con modifier
        character.max_hit_points = hit_die + con_modifier
        character.hit_points = character.max_hit_points
        
        # Base armor class (10 + dex modifier)
        character.armor_class = 10 + character.get_ability_modifier("dexterity")
    
    def _add_class_features(self, character: Character):
        """Add class-specific features, proficiencies, and abilities."""
        char_class = character.character_class.lower()
        
        # Class proficiencies (simplified)
        class_proficiencies = {
            "fighter": {
                "armor": ["Light armor", "Medium armor", "Heavy armor", "Shields"],
                "weapons": ["Simple weapons", "Martial weapons"],
                "saving_throws": ["Strength", "Constitution"],
                "skills": ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"]
            },
            "wizard": {
                "armor": [],
                "weapons": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
                "saving_throws": ["Intelligence", "Wisdom"],
                "skills": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"]
            },
            "rogue": {
                "armor": ["Light armor"],
                "weapons": ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
                "saving_throws": ["Dexterity", "Intelligence"],
                "skills": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"]
            }
        }
        
        proficiencies = class_proficiencies.get(char_class, class_proficiencies["fighter"])
        
        character.armor_proficiencies.extend(proficiencies.get("armor", []))
        character.weapon_proficiencies.extend(proficiencies.get("weapons", []))
        character.saving_throw_proficiencies.extend(proficiencies.get("saving_throws", []))
        
        # Add 2 skill proficiencies for most classes
        available_skills = proficiencies.get("skills", [])
        if len(available_skills) >= 2:
            character.skill_proficiencies.extend(available_skills[:2])
        
        # Add class features
        if char_class == "fighter":
            character.features.append(CharacterFeature(
                name="Fighting Style",
                description="Choose a fighting style: Archery, Defense, Dueling, Great Weapon Fighting, Protection, or Two-Weapon Fighting.",
                source="class"
            ))
            character.features.append(CharacterFeature(
                name="Second Wind",
                description="You can use a bonus action to regain 1d10 + fighter level hit points.",
                source="class",
                uses_per_rest=1,
                rest_type="short"
            ))
        elif char_class == "wizard":
            character.features.append(CharacterFeature(
                name="Spellcasting",
                description="You are a 1st-level spellcaster. Your spellcasting ability is Intelligence.",
                source="class"
            ))
            character.features.append(CharacterFeature(
                name="Arcane Recovery",
                description="You can recover some expended spell slots during a short rest.",
                source="class"
            ))
        elif char_class == "rogue":
            character.features.append(CharacterFeature(
                name="Expertise",
                description="Choose two skill proficiencies. Your proficiency bonus is doubled for ability checks using these skills.",
                source="class"
            ))
            character.features.append(CharacterFeature(
                name="Sneak Attack",
                description="Deal an extra 1d6 damage when you have advantage on the attack roll.",
                source="class"
            ))
            character.features.append(CharacterFeature(
                name="Thieves' Cant",
                description="You know thieves' cant, a secret mix of dialect, jargon, and code.",
                source="class"
            ))
    
    def _add_background_features(self, character: Character):
        """Add background-specific features and proficiencies."""
        background = character.background.lower().replace(" ", "_")
        
        # Background proficiencies and features (simplified)
        background_data = {
            "soldier": {
                "skills": ["Athletics", "Intimidation"],
                "tools": ["One type of gaming set", "Vehicles (land)"],
                "languages": ["One of your choice"],
                "feature": CharacterFeature(
                    name="Military Rank",
                    description="You have a military rank and soldiers loyal to you recognize your authority.",
                    source="background"
                )
            },
            "folk_hero": {
                "skills": ["Animal Handling", "Survival"],
                "tools": ["One type of artisan's tools", "Vehicles (land)"],
                "languages": [],
                "feature": CharacterFeature(
                    name="Rustic Hospitality",
                    description="Common folk will provide you with simple accommodations and food.",
                    source="background"
                )
            },
            "acolyte": {
                "skills": ["Insight", "Religion"],
                "tools": [],
                "languages": ["Two of your choice"],
                "feature": CharacterFeature(
                    name="Shelter of the Faithful",
                    description="You can receive free healing and care at temples of your faith.",
                    source="background"
                )
            }
        }
        
        bg_data = background_data.get(background, background_data["folk_hero"])
        
        # Add skills (if not already proficient)
        for skill in bg_data["skills"]:
            if skill not in character.skill_proficiencies:
                character.skill_proficiencies.append(skill)
        
        # Add tools
        character.tool_proficiencies.extend(bg_data["tools"])
        
        # Add feature
        character.features.append(bg_data["feature"])
    
    def _add_starting_equipment(self, character: Character):
        """Add starting equipment based on class and background."""
        char_class = character.character_class.lower()
        
        # Starting equipment by class (simplified)
        if char_class == "fighter":
            character.equipment.extend([
                EquipmentItem(
                    name="Chain mail",
                    item_type="armor",
                    armor_class=16,
                    description="Heavy armor that provides excellent protection"
                ),
                EquipmentItem(
                    name="Shield",
                    item_type="shield",
                    ac_bonus=2,
                    description="A wooden or metal shield"
                ),
                EquipmentItem(
                    name="Longsword",
                    item_type="weapon",
                    damage="1d8",
                    damage_type="slashing",
                    description="A versatile martial weapon"
                ),
                EquipmentItem(
                    name="Javelin",
                    item_type="weapon",
                    damage="1d6",
                    damage_type="piercing",
                    quantity=4,
                    range_normal=30,
                    range_long=120,
                    description="A light thrown weapon"
                )
            ])
        elif char_class == "wizard":
            character.equipment.extend([
                EquipmentItem(
                    name="Quarterstaff",
                    item_type="weapon",
                    damage="1d6",
                    damage_type="bludgeoning",
                    description="A simple weapon"
                ),
                EquipmentItem(
                    name="Spellbook",
                    item_type="equipment",
                    description="Contains your known spells"
                ),
                EquipmentItem(
                    name="Component pouch",
                    item_type="equipment",
                    description="For spellcasting components"
                )
            ])
        elif char_class == "rogue":
            character.equipment.extend([
                EquipmentItem(
                    name="Leather armor",
                    item_type="armor",
                    armor_class=11,
                    description="Light armor made of leather"
                ),
                EquipmentItem(
                    name="Shortsword",
                    item_type="weapon",
                    damage="1d6",
                    damage_type="piercing",
                    description="A light, finesse weapon"
                ),
                EquipmentItem(
                    name="Dagger",
                    item_type="weapon",
                    damage="1d4",
                    damage_type="piercing",
                    quantity=2,
                    description="A light, finesse, thrown weapon"
                ),
                EquipmentItem(
                    name="Thieves' tools",
                    item_type="tools",
                    description="Tools for picking locks and disarming traps"
                )
            ])
        
        # Add basic adventuring gear
        character.equipment.extend([
            EquipmentItem(
                name="Backpack",
                item_type="equipment",
                description="For carrying gear"
            ),
            EquipmentItem(
                name="Bedroll",
                item_type="equipment",
                description="For sleeping outdoors"
            ),
            EquipmentItem(
                name="Rations (10 days)",
                item_type="equipment",
                quantity=10,
                description="Trail rations"
            ),
            EquipmentItem(
                name="Gold pieces",
                item_type="currency",
                quantity=100,
                description="Starting money"
            )
        ])
    
    def save_character(self, character: Character) -> bool:
        """Save character to file system."""
        try:
            character.update_timestamp()
            
            file_path = self.characters_dir / f"{character.id}.json"
            with open(file_path, 'w') as f:
                json.dump(character.to_dict(), f, indent=2)
            
            logger.info(f"Saved character {character.name} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save character {character.id}: {e}")
            return False
    
    def load_character(self, character_id: str) -> Optional[Character]:
        """Load character from file system."""
        # Check cache first
        if character_id in self._character_cache:
            return self._character_cache[character_id]
        
        try:
            file_path = self.characters_dir / f"{character_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert dict back to Character object
            character = self._dict_to_character(data)
            self._character_cache[character_id] = character
            
            return character
            
        except Exception as e:
            logger.error(f"Failed to load character {character_id}: {e}")
            return None
    
    def _dict_to_character(self, data: Dict[str, Any]) -> Character:
        """Convert dictionary to Character object."""
        # Convert ability scores
        ability_data = data.get("ability_scores", {})
        ability_scores = AbilityScores(**ability_data)
        
        # Convert equipment
        equipment = []
        for item_data in data.get("equipment", []):
            equipment.append(EquipmentItem(**item_data))
        
        # Convert features
        features = []
        for feature_data in data.get("features", []):
            features.append(CharacterFeature(**feature_data))
        
        # Create character
        character = Character(
            id=data["id"],
            name=data["name"],
            race=data["race"],
            character_class=data["character_class"],
            background=data["background"],
            level=data.get("level", 1),
            ability_scores=ability_scores,
            hit_points=data.get("hit_points", 0),
            max_hit_points=data.get("max_hit_points", 0),
            armor_class=data.get("armor_class", 10),
            speed=data.get("speed", 30),
            proficiency_bonus=data.get("proficiency_bonus", 2),
            skill_proficiencies=data.get("skill_proficiencies", []),
            saving_throw_proficiencies=data.get("saving_throw_proficiencies", []),
            armor_proficiencies=data.get("armor_proficiencies", []),
            weapon_proficiencies=data.get("weapon_proficiencies", []),
            tool_proficiencies=data.get("tool_proficiencies", []),
            languages=data.get("languages", []),
            equipment=equipment,
            features=features,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            notes=data.get("notes", "")
        )
        
        return character
    
    def list_characters(self) -> List[Character]:
        """List all saved characters."""
        characters = []
        
        try:
            for file_path in self.characters_dir.glob("*.json"):
                character_id = file_path.stem
                character = self.load_character(character_id)
                if character:
                    characters.append(character)
        
        except Exception as e:
            logger.error(f"Failed to list characters: {e}")
        
        return characters
    
    def delete_character(self, character_id: str) -> bool:
        """Delete a character."""
        try:
            file_path = self.characters_dir / f"{character_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            # Remove from cache
            if character_id in self._character_cache:
                del self._character_cache[character_id]
            
            logger.info(f"Deleted character {character_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete character {character_id}: {e}")
            return False
    
    def level_up_character(self, character_id: str) -> Optional[Character]:
        """Level up a character and recalculate stats."""
        character = self.load_character(character_id)
        if not character:
            return None
        
        if character.level >= 20:
            logger.warning(f"Character {character_id} is already max level")
            return character
        
        # Increase level
        character.level += 1
        
        # Update proficiency bonus
        character.proficiency_bonus = self.PROFICIENCY_BONUS_BY_LEVEL.get(character.level, 2)
        
        # Increase hit points (average + con modifier)
        try:
            class_enum = CharacterClass(character.character_class.lower())
        except ValueError:
            class_enum = CharacterClass.FIGHTER
        
        hit_die = self.HIT_DICE_BY_CLASS.get(class_enum, 8)
        con_modifier = character.get_ability_modifier("constitution")
        
        # Use average hit points increase (hit_die / 2 + 1 + con_modifier)
        hp_increase = (hit_die // 2) + 1 + con_modifier
        character.max_hit_points += hp_increase
        character.hit_points += hp_increase
        
        # Add level-appropriate features (this would be more complex in a full implementation)
        if character.level == 2:
            if character.character_class.lower() == "fighter":
                character.features.append(CharacterFeature(
                    name="Action Surge",
                    description="You can take one additional action on your turn.",
                    source="class",
                    level_acquired=2,
                    uses_per_rest=1,
                    rest_type="short"
                ))
        
        # Save updated character
        self.save_character(character)
        
        return character
    
    def validate_character(self, character: Character) -> Tuple[bool, List[str]]:
        """Validate character against D&D 5e rules."""
        errors = []
        
        # Check ability score ranges
        for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            score = getattr(character.ability_scores, ability)
            if score < 1 or score > 30:
                errors.append(f"{ability.title()} score {score} is outside valid range (1-30)")
        
        # Check level range
        if character.level < 1 or character.level > 20:
            errors.append(f"Level {character.level} is outside valid range (1-20)")
        
        # Check hit points
        if character.hit_points < 0:
            errors.append("Hit points cannot be negative")
        
        if character.max_hit_points < 1:
            errors.append("Maximum hit points must be at least 1")
        
        # Check proficiency bonus matches level
        expected_proficiency = self.PROFICIENCY_BONUS_BY_LEVEL.get(character.level, 2)
        if character.proficiency_bonus != expected_proficiency:
            errors.append(f"Proficiency bonus {character.proficiency_bonus} doesn't match level {character.level} (expected {expected_proficiency})")
        
        return len(errors) == 0, errors
    
    def get_character_summary(self, character: Character) -> Dict[str, Any]:
        """Get a summary of character stats and abilities."""
        return {
            "basic_info": {
                "name": character.name,
                "race": character.race,
                "class": character.character_class,
                "background": character.background,
                "level": character.level
            },
            "ability_scores": character.ability_scores.to_dict(),
            "ability_modifiers": character.ability_scores.get_all_modifiers(),
            "combat_stats": {
                "hit_points": f"{character.hit_points}/{character.max_hit_points}",
                "armor_class": character.armor_class,
                "speed": character.speed,
                "proficiency_bonus": character.proficiency_bonus
            },
            "saving_throws": {
                ability: character.get_saving_throw_modifier(ability)
                for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
            },
            "skill_proficiencies": character.skill_proficiencies,
            "features_count": len(character.features),
            "equipment_count": len(character.equipment)
        }


# Global service instance
character_service = CharacterService() 