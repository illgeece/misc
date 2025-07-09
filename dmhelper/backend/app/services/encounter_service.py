"""Encounter generation service for D&D 5e with CR balancing and tactical recommendations."""

import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class EncounterDifficulty(Enum):
    """D&D 5e encounter difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    DEADLY = "deadly"


class Environment(Enum):
    """Encounter environments/terrains."""
    DUNGEON = "dungeon"
    FOREST = "forest"
    MOUNTAINS = "mountains"
    SWAMP = "swamp"
    DESERT = "desert"
    COAST = "coast"
    URBAN = "urban"
    UNDERGROUND = "underground"
    PLANAR = "planar"
    ARCTIC = "arctic"
    GRASSLAND = "grassland"
    HILL = "hill"


class CreatureSize(Enum):
    """Creature size categories."""
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"


class CreatureType(Enum):
    """D&D 5e creature types."""
    ABERRATION = "aberration"
    BEAST = "beast"
    CELESTIAL = "celestial"
    CONSTRUCT = "construct"
    DRAGON = "dragon"
    ELEMENTAL = "elemental"
    FEY = "fey"
    FIEND = "fiend"
    GIANT = "giant"
    HUMANOID = "humanoid"
    MONSTROSITY = "monstrosity"
    OOZE = "ooze"
    PLANT = "plant"
    UNDEAD = "undead"


@dataclass
class PartyComposition:
    """Represents the party composition for encounter balancing."""
    party_size: int
    party_level: int
    average_level: Optional[float] = None
    characters: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.average_level is None:
            self.average_level = float(self.party_level)


@dataclass 
class Monster:
    """Represents a monster/creature for encounters."""
    name: str
    challenge_rating: str  # e.g., "1/4", "1", "10"
    xp_value: int
    creature_type: CreatureType
    size: CreatureSize
    armor_class: int
    hit_points: int
    environments: List[Environment]
    description: str = ""
    tactics: str = ""
    special_abilities: List[str] = field(default_factory=list)
    damage_resistances: List[str] = field(default_factory=list)
    damage_immunities: List[str] = field(default_factory=list)
    condition_immunities: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    
    @property
    def cr_numeric(self) -> float:
        """Convert CR string to numeric value for calculations."""
        if self.challenge_rating == "0":
            return 0.0
        elif self.challenge_rating == "1/8":
            return 0.125
        elif self.challenge_rating == "1/4":
            return 0.25
        elif self.challenge_rating == "1/2":
            return 0.5
        else:
            try:
                return float(self.challenge_rating)
            except ValueError:
                return 0.0


@dataclass
class EncounterMonster:
    """Represents a monster instance in an encounter."""
    monster: Monster
    count: int = 1
    initiative_modifier: int = 0
    special_notes: str = ""
    
    @property
    def total_xp(self) -> int:
        """Total XP for all instances of this monster."""
        return self.monster.xp_value * self.count


@dataclass
class GeneratedEncounter:
    """Represents a complete generated encounter."""
    encounter_id: str
    party_composition: PartyComposition
    difficulty: EncounterDifficulty
    environment: Environment
    monsters: List[EncounterMonster]
    total_xp: int
    adjusted_xp: int
    xp_budget: int
    encounter_multiplier: float
    tactical_notes: str = ""
    environmental_features: List[str] = field(default_factory=list)
    
    @property
    def total_monster_count(self) -> int:
        """Total number of individual monsters in the encounter."""
        return sum(em.count for em in self.monsters)
    
    @property
    def average_cr(self) -> float:
        """Average challenge rating of monsters in the encounter."""
        if not self.monsters:
            return 0.0
        
        total_cr = sum(em.monster.cr_numeric * em.count for em in self.monsters)
        return total_cr / self.total_monster_count


class EncounterService:
    """Service for generating balanced D&D 5e encounters."""
    
    # D&D 5e XP budget per character by level and difficulty
    XP_BUDGET_TABLE = {
        1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
        2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
        3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
        4: {"easy": 125, "medium": 250, "hard": 375, "deadly": 500},
        5: {"easy": 250, "medium": 500, "hard": 750, "deadly": 1100},
        6: {"easy": 300, "medium": 600, "hard": 900, "deadly": 1400},
        7: {"easy": 350, "medium": 750, "hard": 1100, "deadly": 1700},
        8: {"easy": 450, "medium": 900, "hard": 1400, "deadly": 2100},
        9: {"easy": 550, "medium": 1100, "hard": 1600, "deadly": 2400},
        10: {"easy": 600, "medium": 1200, "hard": 1900, "deadly": 2800},
        11: {"easy": 800, "medium": 1600, "hard": 2400, "deadly": 3600},
        12: {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4500},
        13: {"easy": 1100, "medium": 2200, "hard": 3400, "deadly": 5100},
        14: {"easy": 1250, "medium": 2500, "hard": 3800, "deadly": 5700},
        15: {"easy": 1400, "medium": 2800, "hard": 4300, "deadly": 6400},
        16: {"easy": 1600, "medium": 3200, "hard": 4800, "deadly": 7200},
        17: {"easy": 2000, "medium": 3900, "hard": 5900, "deadly": 8800},
        18: {"easy": 2100, "medium": 4200, "hard": 6300, "deadly": 9500},
        19: {"easy": 2400, "medium": 4900, "hard": 7300, "deadly": 10900},
        20: {"easy": 2800, "medium": 5700, "hard": 8500, "deadly": 12700}
    }
    
    # Encounter multipliers based on number of monsters
    ENCOUNTER_MULTIPLIERS = {
        1: 1.0,
        2: 1.5,
        (3, 6): 2.0,
        (7, 10): 2.5,
        (11, 14): 3.0,
        (15, float('inf')): 4.0
    }
    
    def __init__(self):
        self.monster_database: Dict[str, Monster] = {}
        self._initialize_monster_database()
    
    def _initialize_monster_database(self):
        """Initialize the monster database with core D&D 5e monsters."""
        # Basic monsters for testing and initial implementation
        core_monsters = [
            Monster(
                name="Goblin",
                challenge_rating="1/4",
                xp_value=50,
                creature_type=CreatureType.HUMANOID,
                size=CreatureSize.SMALL,
                armor_class=15,
                hit_points=7,
                environments=[Environment.FOREST, Environment.HILL, Environment.MOUNTAINS],
                tactics="Goblins prefer to fight in groups, using their nimbleness to dart in and out of combat. They favor hit-and-run tactics and will flee if reduced to half numbers.",
                special_abilities=["Nimble Escape"]
            ),
            Monster(
                name="Orc",
                challenge_rating="1/2",
                xp_value=100,
                creature_type=CreatureType.HUMANOID,
                size=CreatureSize.MEDIUM,
                armor_class=13,
                hit_points=15,
                environments=[Environment.FOREST, Environment.HILL, Environment.MOUNTAINS, Environment.UNDERGROUND],
                tactics="Orcs fight aggressively and prefer direct combat. They become more dangerous when bloodied.",
                special_abilities=["Aggressive"]
            ),
            Monster(
                name="Wolf",
                challenge_rating="1/4",
                xp_value=50,
                creature_type=CreatureType.BEAST,
                size=CreatureSize.MEDIUM,
                armor_class=13,
                hit_points=11,
                environments=[Environment.FOREST, Environment.HILL, Environment.ARCTIC],
                tactics="Wolves hunt in packs, attempting to knock prone isolated targets. They use pack tactics to gain advantage on attacks.",
                special_abilities=["Pack Tactics", "Keen Hearing and Smell"]
            ),
            Monster(
                name="Brown Bear",
                challenge_rating="1",
                xp_value=200,
                creature_type=CreatureType.BEAST,
                size=CreatureSize.LARGE,
                armor_class=11,
                hit_points=34,
                environments=[Environment.FOREST, Environment.HILL, Environment.MOUNTAINS],
                tactics="Bears are territorial and aggressive. They will maul and grapple opponents, focusing on the nearest threat.",
                special_abilities=["Keen Smell"]
            ),
            Monster(
                name="Ogre",
                challenge_rating="2",
                xp_value=450,
                creature_type=CreatureType.GIANT,
                size=CreatureSize.LARGE,
                armor_class=11,
                hit_points=59,
                environments=[Environment.HILL, Environment.MOUNTAINS, Environment.FOREST],
                tactics="Ogres are simple but deadly combatants. They charge the strongest-looking opponents and fight to the death.",
                special_abilities=[]
            ),
            Monster(
                name="Owlbear",
                challenge_rating="3",
                xp_value=700,
                creature_type=CreatureType.MONSTROSITY,
                size=CreatureSize.LARGE,
                armor_class=13,
                hit_points=59,
                environments=[Environment.FOREST],
                tactics="Owlbears are ferocious predators that attack with both claw and beak. They fight until death.",
                special_abilities=["Keen Sight and Smell"]
            ),
            Monster(
                name="Hill Giant",
                challenge_rating="5",
                xp_value=1800,
                creature_type=CreatureType.GIANT,
                size=CreatureSize.HUGE,
                armor_class=13,
                hit_points=105,
                environments=[Environment.HILL, Environment.MOUNTAINS],
                tactics="Hill giants throw rocks at range before closing to melee. They target spellcasters and ranged attackers first.",
                special_abilities=["Rock"]
            ),
            Monster(
                name="Troll",
                challenge_rating="5",
                xp_value=1800,
                creature_type=CreatureType.GIANT,
                size=CreatureSize.LARGE,
                armor_class=15,
                hit_points=84,
                environments=[Environment.SWAMP, Environment.FOREST, Environment.MOUNTAINS],
                tactics="Trolls regenerate unless damaged by acid or fire. They fight recklessly, trusting in their regeneration.",
                special_abilities=["Regeneration", "Keen Smell"]
            ),
            Monster(
                name="Skeleton",
                challenge_rating="1/4",
                xp_value=50,
                creature_type=CreatureType.UNDEAD,
                size=CreatureSize.MEDIUM,
                armor_class=13,
                hit_points=13,
                environments=[Environment.DUNGEON, Environment.UNDERGROUND],
                tactics="Skeletons follow simple commands and fight without fear or self-preservation instincts.",
                special_abilities=["Damage Vulnerabilities (bludgeoning)"],
                condition_immunities=["exhaustion", "poisoned"]
            ),
            Monster(
                name="Zombie",
                challenge_rating="1/4",
                xp_value=50,
                creature_type=CreatureType.UNDEAD,
                size=CreatureSize.MEDIUM,
                armor_class=8,
                hit_points=22,
                environments=[Environment.DUNGEON, Environment.URBAN],
                tactics="Zombies shamble toward the nearest living creature and attack mindlessly. They can survive mortal wounds temporarily.",
                special_abilities=["Undead Fortitude"],
                condition_immunities=["poisoned"]
            )
        ]
        
        for monster in core_monsters:
            self.monster_database[monster.name.lower()] = monster
        
        logger.info(f"Initialized monster database with {len(self.monster_database)} creatures")
    
    def get_xp_budget(self, party_composition: PartyComposition, difficulty: EncounterDifficulty) -> int:
        """Calculate the XP budget for an encounter."""
        level = min(20, max(1, int(party_composition.average_level)))
        budget_per_character = self.XP_BUDGET_TABLE[level][difficulty.value]
        return budget_per_character * party_composition.party_size
    
    def get_encounter_multiplier(self, monster_count: int) -> float:
        """Get the encounter multiplier based on number of monsters."""
        for key, multiplier in self.ENCOUNTER_MULTIPLIERS.items():
            if isinstance(key, int):
                if monster_count == key:
                    return multiplier
            elif isinstance(key, tuple):
                min_count, max_count = key
                if min_count <= monster_count <= max_count:
                    return multiplier
        return 4.0  # Default for very large groups
    
    def calculate_encounter_xp(self, monsters: List[EncounterMonster]) -> Tuple[int, int, float]:
        """Calculate total XP, adjusted XP, and multiplier for an encounter."""
        total_xp = sum(em.total_xp for em in monsters)
        monster_count = sum(em.count for em in monsters)
        multiplier = self.get_encounter_multiplier(monster_count)
        adjusted_xp = int(total_xp * multiplier)
        
        return total_xp, adjusted_xp, multiplier
    
    def get_monsters_by_environment(self, environment: Environment) -> List[Monster]:
        """Get all monsters suitable for a specific environment."""
        return [
            monster for monster in self.monster_database.values()
            if environment in monster.environments
        ]
    
    def get_monsters_by_cr_range(self, min_cr: float, max_cr: float) -> List[Monster]:
        """Get monsters within a CR range."""
        return [
            monster for monster in self.monster_database.values()
            if min_cr <= monster.cr_numeric <= max_cr
        ]
    
    def suggest_monsters_for_budget(
        self,
        xp_budget: int,
        environment: Environment,
        party_level: int,
        max_monsters: int = 8
    ) -> List[Tuple[Monster, int]]:
        """Suggest monsters and quantities that fit within the XP budget."""
        suitable_monsters = self.get_monsters_by_environment(environment)
        
        # Filter monsters by appropriate CR range (roughly party level -2 to +3)
        min_cr = max(0, party_level - 2)
        max_cr = party_level + 3
        
        suitable_monsters = [
            m for m in suitable_monsters
            if min_cr <= m.cr_numeric <= max_cr
        ]
        
        suggestions = []
        
        for monster in suitable_monsters:
            # Calculate how many of this monster we could include
            max_count = min(max_monsters, xp_budget // monster.xp_value)
            
            for count in range(1, max_count + 1):
                total_xp = monster.xp_value * count
                multiplier = self.get_encounter_multiplier(count)
                adjusted_xp = int(total_xp * multiplier)
                
                if adjusted_xp <= xp_budget:
                    suggestions.append((monster, count))
        
        # Sort by how close the adjusted XP is to the budget
        suggestions.sort(key=lambda x: abs(xp_budget - (x[0].xp_value * x[1] * self.get_encounter_multiplier(x[1]))))
        
        return suggestions[:10]  # Return top 10 suggestions
    
    def generate_encounter(
        self,
        party_composition: PartyComposition,
        difficulty: EncounterDifficulty,
        environment: Environment,
        encounter_theme: Optional[str] = None,
        required_monsters: Optional[List[EncounterMonster]] = None
    ) -> GeneratedEncounter:
        """Generate a balanced encounter for the given parameters."""
        
        xp_budget = self.get_xp_budget(party_composition, difficulty)
        party_level = int(party_composition.average_level)
        
        # Get suitable monsters using the improved method with fallbacks
        suitable_monsters = self.get_suitable_monsters(party_level, environment, xp_budget)
        
        if not suitable_monsters:
            logger.error(f"No suitable monsters found even with fallbacks for party level {party_level}")
            # Create an emergency basic encounter
            return self._create_emergency_encounter(party_composition, difficulty, environment)
        
        # Initialize with any required monsters specified by caller
        encounter_monsters: List[EncounterMonster] = []
        if required_monsters:
            encounter_monsters.extend(required_monsters)

        # Calculate remaining XP budget after accounting for required monsters
        _, existing_adjusted_xp, _ = (
            self.calculate_encounter_xp(encounter_monsters) if encounter_monsters else (0, 0, 1.0)
        )
        remaining_budget = max(0, xp_budget - existing_adjusted_xp)

        # Remove required monsters from candidate list to avoid duplicates
        required_names: Set[str] = {em.monster.name.lower() for em in encounter_monsters}
        remaining_candidates = [m for m in suitable_monsters if m.name.lower() not in required_names]

        # Generate additional composition to fill remaining budget
        generated_monsters = self._generate_encounter_composition(
            remaining_candidates if remaining_candidates else suitable_monsters,
            remaining_budget,
            difficulty,
        )
        encounter_monsters.extend(generated_monsters)
        
        # Calculate final XP values
        total_xp, adjusted_xp, multiplier = self.calculate_encounter_xp(encounter_monsters)
        
        # Generate tactical notes
        tactical_notes = self._generate_tactical_notes(encounter_monsters, environment)
        
        # Generate environmental features
        environmental_features = self._generate_environmental_features(environment)
        
        encounter = GeneratedEncounter(
            encounter_id=f"enc_{random.randint(1000, 9999)}",
            party_composition=party_composition,
            difficulty=difficulty,
            environment=environment,
            monsters=encounter_monsters,
            total_xp=total_xp,
            adjusted_xp=adjusted_xp,
            xp_budget=xp_budget,
            encounter_multiplier=multiplier,
            tactical_notes=tactical_notes,
            environmental_features=environmental_features
        )
        
        logger.info(f"Generated {difficulty.value} encounter for {party_composition.party_size} level {party_level} characters")
        logger.info(f"XP Budget: {xp_budget}, Adjusted XP: {adjusted_xp}, Monsters: {len(encounter_monsters)}")
        
        return encounter
    
    def _generate_encounter_composition(
        self,
        suitable_monsters: List[Monster],
        xp_budget: int,
        difficulty: EncounterDifficulty
    ) -> List[EncounterMonster]:
        """Generate the actual monster composition for an encounter."""
        encounter_monsters = []
        remaining_budget = xp_budget
        max_attempts = 50
        
        # Determine encounter style based on difficulty
        if difficulty in [EncounterDifficulty.EASY, EncounterDifficulty.MEDIUM]:
            # Prefer fewer, stronger monsters or small groups
            preferred_count_range = (1, 4)
        else:
            # Hard/deadly can have more monsters
            preferred_count_range = (1, 8)
        
        for attempt in range(max_attempts):
            if remaining_budget <= 50:  # Stop if budget is very low
                break
            
            # Select a random monster
            monster = random.choice(suitable_monsters)
            
            # Determine how many we can afford
            max_affordable = remaining_budget // monster.xp_value
            if max_affordable == 0:
                continue
            
            # Choose count within preferred range
            max_count = min(max_affordable, preferred_count_range[1])
            if max_count == 0:
                continue
            
            count = random.randint(1, max_count)
            
            # Calculate if this addition would fit in budget
            total_monsters_after = sum(em.count for em in encounter_monsters) + count
            multiplier = self.get_encounter_multiplier(total_monsters_after)
            
            # Calculate total adjusted XP after this addition
            current_xp = sum(em.total_xp for em in encounter_monsters)
            new_total_xp = current_xp + (monster.xp_value * count)
            adjusted_xp = int(new_total_xp * multiplier)
            
            # Check if it fits in budget (with some tolerance)
            if adjusted_xp <= xp_budget * 1.1:  # 10% tolerance
                encounter_monsters.append(EncounterMonster(monster=monster, count=count))
                remaining_budget = max(0, xp_budget - adjusted_xp)
                
                # If we're close to budget, stop
                if adjusted_xp >= xp_budget * 0.9:
                    break
        
        # If no monsters were added, try to add one ignoring budget constraints
        if not encounter_monsters and suitable_monsters:
            # First try monsters that fit in budget
            fallback_monsters = [m for m in suitable_monsters if m.xp_value <= xp_budget]
            if fallback_monsters:
                monster = max(fallback_monsters, key=lambda m: m.xp_value)
                encounter_monsters.append(EncounterMonster(monster=monster, count=1))
            else:
                # If no monsters fit budget, use the cheapest available monster anyway
                # This handles cases where budget is too small for any monster
                cheapest_monster = min(suitable_monsters, key=lambda m: m.xp_value)
                encounter_monsters.append(EncounterMonster(monster=cheapest_monster, count=1))
        
        return encounter_monsters
    
    def _generate_tactical_notes(self, monsters: List[EncounterMonster], environment: Environment) -> str:
        """Generate tactical recommendations for running the encounter."""
        notes = []
        
        # Analyze monster composition
        total_monsters = sum(em.count for em in monsters)
        monster_types = set(em.monster.creature_type for em in monsters)
        
        if total_monsters == 1:
            monster = monsters[0].monster
            notes.append(f"Single {monster.name} encounter - focus on the creature's special abilities.")
            if monster.tactics:
                notes.append(f"Tactics: {monster.tactics}")
        else:
            notes.append(f"Multi-creature encounter with {total_monsters} total opponents.")
            
            # Group tactics
            if len(monsters) > 1:
                notes.append("Consider having monsters coordinate their attacks and positioning.")
            
            # Type-specific tactics
            if CreatureType.UNDEAD in monster_types:
                notes.append("Undead creatures are immune to many conditions and fight fearlessly.")
            
            if CreatureType.BEAST in monster_types:
                notes.append("Beasts may use pack tactics and attempt to flank opponents.")
            
            if CreatureType.HUMANOID in monster_types:
                notes.append("Intelligent humanoids may use terrain, cover, and coordinated tactics.")
        
        # Environmental tactical considerations
        env_tactics = {
            Environment.FOREST: "Use trees for cover and concealment. Consider ambush tactics.",
            Environment.DUNGEON: "Utilize confined spaces, doorways, and corridors strategically.",
            Environment.MOUNTAINS: "Height advantages and difficult terrain can favor defenders.",
            Environment.SWAMP: "Difficult terrain and poor visibility affect movement and targeting.",
            Environment.URBAN: "Civilians, buildings, and vertical terrain create complex scenarios."
        }
        
        if environment in env_tactics:
            notes.append(f"Environment: {env_tactics[environment]}")
        
        return " ".join(notes)
    
    def _generate_environmental_features(self, environment: Environment) -> List[str]:
        """Generate environmental features that can affect the encounter."""
        features_by_environment = {
            Environment.FOREST: [
                "Dense undergrowth (difficult terrain)",
                "Large trees provide cover",
                "Fallen logs create barriers",
                "Thick canopy limits visibility"
            ],
            Environment.DUNGEON: [
                "Stone pillars provide cover",
                "Narrow corridors limit movement",
                "Alcoves and doorways offer tactical positions",
                "Poor lighting conditions"
            ],
            Environment.MOUNTAINS: [
                "Rocky outcroppings provide cover",
                "Steep slopes (difficult terrain)",
                "Loose rocks may cause slides",
                "High altitude affects endurance"
            ],
            Environment.SWAMP: [
                "Murky water obscures footing",
                "Thick vegetation blocks sight lines",
                "Muddy ground (difficult terrain)",
                "Poisonous plants and insects"
            ],
            Environment.URBAN: [
                "Buildings provide cover and elevation",
                "Streets channel movement",
                "Crowds may interfere",
                "Varied terrain elevation"
            ]
        }
        
        base_features = features_by_environment.get(environment, ["Open terrain with few obstacles"])
        
        # Randomly select 2-3 features
        selected_count = min(len(base_features), random.randint(2, 3))
        return random.sample(base_features, selected_count)
    
    def assess_encounter_difficulty(
        self,
        monsters: List[EncounterMonster],
        party_composition: PartyComposition
    ) -> Tuple[EncounterDifficulty, Dict[str, Any]]:
        """Assess the difficulty of an encounter and provide analysis."""
        
        total_xp, adjusted_xp, multiplier = self.calculate_encounter_xp(monsters)
        
        # Get thresholds for each difficulty
        party_level = int(party_composition.average_level)
        thresholds = {}
        
        for difficulty in EncounterDifficulty:
            threshold = self.get_xp_budget(party_composition, difficulty)
            thresholds[difficulty.value] = threshold
        
        # Determine actual difficulty
        actual_difficulty = EncounterDifficulty.EASY
        
        if adjusted_xp >= thresholds["deadly"]:
            actual_difficulty = EncounterDifficulty.DEADLY
        elif adjusted_xp >= thresholds["hard"]:
            actual_difficulty = EncounterDifficulty.HARD
        elif adjusted_xp >= thresholds["medium"]:
            actual_difficulty = EncounterDifficulty.MEDIUM
        
        analysis = {
            "total_xp": total_xp,
            "adjusted_xp": adjusted_xp,
            "encounter_multiplier": multiplier,
            "thresholds": thresholds,
            "monster_count": sum(em.count for em in monsters),
            "average_cr": sum(em.monster.cr_numeric * em.count for em in monsters) / sum(em.count for em in monsters) if monsters else 0
        }
        
        return actual_difficulty, analysis
    
    def get_monster_summary(self) -> Dict[str, Any]:
        """Get a summary of available monsters in the database."""
        summary = {
            "total_monsters": len(self.monster_database),
            "by_type": {},
            "by_environment": {},
            "by_cr": {},
            "cr_range": {"min": float('inf'), "max": 0}
        }
        
        for monster in self.monster_database.values():
            # By type
            type_name = monster.creature_type.value
            summary["by_type"][type_name] = summary["by_type"].get(type_name, 0) + 1
            
            # By environment
            for env in monster.environments:
                env_name = env.value
                summary["by_environment"][env_name] = summary["by_environment"].get(env_name, 0) + 1
            
            # By CR
            cr = monster.challenge_rating
            summary["by_cr"][cr] = summary["by_cr"].get(cr, 0) + 1
            
            # CR range
            cr_numeric = monster.cr_numeric
            summary["cr_range"]["min"] = min(summary["cr_range"]["min"], cr_numeric)
            summary["cr_range"]["max"] = max(summary["cr_range"]["max"], cr_numeric)
        
        return summary

    def get_suitable_monsters(self, party_level: int, environment: Environment, 
                             xp_budget: int, max_monsters: int = 8) -> List[Monster]:
        """Get monsters suitable for a party level and environment with fallback options."""
        # Get base CR range
        min_cr = max(0, party_level / 4 - 1)
        max_cr = party_level + 2
        
        # Get monsters for environment and CR range
        suitable = []
        for monster in self.monster_database.values():
            if (environment in monster.environments and 
                min_cr <= monster.cr_numeric <= max_cr and 
                monster.xp_value <= xp_budget):
                suitable.append(monster)
        
        # If no monsters found, expand search criteria
        if not suitable:
            # Try without environment restriction
            for monster in self.monster_database.values():
                if (min_cr <= monster.cr_numeric <= max_cr and 
                    monster.xp_value <= xp_budget):
                    suitable.append(monster)
        
        # If still no monsters, expand CR range
        if not suitable:
            min_cr = 0
            max_cr = party_level + 4
            for monster in self.monster_database.values():
                if (min_cr <= monster.cr_numeric <= max_cr and 
                    monster.xp_value <= xp_budget * 2):  # Also expand budget
                    suitable.append(monster)
        
        # As absolute fallback, return all monsters that fit in budget
        if not suitable:
            for monster in self.monster_database.values():
                if monster.xp_value <= xp_budget * 3:
                    suitable.append(monster)
        
        # Ensure we have at least some basic monsters as final fallback
        if not suitable:
            basic_monsters = ["goblin", "orc", "wolf", "bear"]
            for monster_name in basic_monsters:
                if monster_name in self.monster_database:
                    suitable.append(self.monster_database[monster_name])
        
        return suitable[:max_monsters]

    def _create_emergency_encounter(self, party_composition: PartyComposition, 
                                  difficulty: EncounterDifficulty, environment: Environment) -> GeneratedEncounter:
        """Create a basic encounter when no suitable monsters are found."""
        encounter_id = f"enc_{self._generate_id()}"
        xp_budget = self.get_xp_budget(party_composition, difficulty)
        
        # Use goblin as the basic fallback monster
        if "goblin" in self.monster_database:
            fallback_monster = self.monster_database["goblin"]
        else:
            # Use any available monster as absolute fallback
            fallback_monster = list(self.monster_database.values())[0]
        
        # Calculate appropriate count for the budget
        if fallback_monster.xp_value > 0:
            count = max(1, min(8, xp_budget // fallback_monster.xp_value))
        else:
            count = 1
        
        encounter_monsters = [EncounterMonster(monster=fallback_monster, count=count)]
        
        total_xp, adjusted_xp, multiplier = self.calculate_encounter_xp(encounter_monsters)
        
        return GeneratedEncounter(
            encounter_id=encounter_id,
            party_composition=party_composition,
            difficulty=difficulty,
            environment=environment,
            monsters=encounter_monsters,
            total_xp=total_xp,
            adjusted_xp=adjusted_xp,
            xp_budget=xp_budget,
            encounter_multiplier=multiplier,
            tactical_notes="Emergency encounter - basic monsters only.",
            environmental_features=["Open terrain"]
        )


# Global encounter service instance
encounter_service = EncounterService() 