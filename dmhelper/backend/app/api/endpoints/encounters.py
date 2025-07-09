"""API endpoints for D&D 5e encounter generation and management."""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.encounter_service import (
    encounter_service, EncounterDifficulty, Environment, PartyComposition,
    GeneratedEncounter, EncounterMonster, Monster
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class PartyCompositionRequest(BaseModel):
    party_size: int = Field(..., ge=1, le=8, description="Number of characters in the party")
    party_level: int = Field(..., ge=1, le=20, description="Average party level")
    characters: Optional[List[Dict[str, Any]]] = Field(default=None, description="Individual character details (optional)")


class RequiredMonsterRequest(BaseModel):
    monster_name: str = Field(..., description="Name of the monster to include")
    count: int = Field(default=1, ge=1, le=12, description="Number of instances of the monster")


class EncounterGenerationRequest(BaseModel):
    party_composition: PartyCompositionRequest
    difficulty: EncounterDifficulty
    environment: Optional[Environment] = Field(default=None, description="Encounter environment; if omitted, the system will choose based on monsters or default")
    encounter_theme: Optional[str] = Field(default=None, description="Optional thematic guidance")
    required_monsters: Optional[List[RequiredMonsterRequest]] = Field(
        default=None, description="Monsters that must be included in the encounter"
    )


class MonsterResponse(BaseModel):
    name: str
    challenge_rating: str
    xp_value: int
    creature_type: str
    size: str
    armor_class: int
    hit_points: int
    environments: List[str]
    description: str
    tactics: str
    special_abilities: List[str]
    

class EncounterMonsterResponse(BaseModel):
    monster: MonsterResponse
    count: int
    total_xp: int
    special_notes: str


class EncounterResponse(BaseModel):
    encounter_id: str
    party_composition: PartyCompositionRequest
    difficulty: str
    environment: str
    monsters: List[EncounterMonsterResponse]
    total_xp: int
    adjusted_xp: int
    xp_budget: int
    encounter_multiplier: float
    total_monster_count: int
    average_cr: float
    tactical_notes: str
    environmental_features: List[str]


class DifficultyAssessmentRequest(BaseModel):
    party_composition: PartyCompositionRequest
    monsters: List[Dict[str, Any]]  # List of {monster_name: str, count: int}


class DifficultyAssessmentResponse(BaseModel):
    assessed_difficulty: str
    total_xp: int
    adjusted_xp: int
    encounter_multiplier: float
    xp_thresholds: Dict[str, int]
    monster_count: int
    average_cr: float
    recommendations: List[str]


class MonsterSuggestionRequest(BaseModel):
    party_level: int = Field(..., ge=1, le=20)
    xp_budget: int = Field(..., ge=1)
    environment: Environment
    max_monsters: int = Field(default=8, ge=1, le=20)


class MonsterSuggestionResponse(BaseModel):
    monster: MonsterResponse
    suggested_count: int
    total_xp: int
    adjusted_xp: int


# Utility functions
def _convert_monster_to_response(monster: Monster) -> MonsterResponse:
    """Convert Monster object to API response format."""
    return MonsterResponse(
        name=monster.name,
        challenge_rating=monster.challenge_rating,
        xp_value=monster.xp_value,
        creature_type=monster.creature_type.value,
        size=monster.size.value,
        armor_class=monster.armor_class,
        hit_points=monster.hit_points,
        environments=[env.value for env in monster.environments],
        description=monster.description,
        tactics=monster.tactics,
        special_abilities=monster.special_abilities
    )


def _convert_encounter_to_response(encounter: GeneratedEncounter) -> EncounterResponse:
    """Convert GeneratedEncounter to API response format."""
    monster_responses = []
    for em in encounter.monsters:
        monster_resp = EncounterMonsterResponse(
            monster=_convert_monster_to_response(em.monster),
            count=em.count,
            total_xp=em.total_xp,
            special_notes=em.special_notes
        )
        monster_responses.append(monster_resp)
    
    return EncounterResponse(
        encounter_id=encounter.encounter_id,
        party_composition=PartyCompositionRequest(
            party_size=encounter.party_composition.party_size,
            party_level=encounter.party_composition.party_level,
            characters=encounter.party_composition.characters
        ),
        difficulty=encounter.difficulty.value,
        environment=encounter.environment.value,
        monsters=monster_responses,
        total_xp=encounter.total_xp,
        adjusted_xp=encounter.adjusted_xp,
        xp_budget=encounter.xp_budget,
        encounter_multiplier=encounter.encounter_multiplier,
        total_monster_count=encounter.total_monster_count,
        average_cr=encounter.average_cr,
        tactical_notes=encounter.tactical_notes,
        environmental_features=encounter.environmental_features
    )


# API Endpoints
@router.post("/generate", response_model=EncounterResponse, summary="Generate a balanced encounter")
async def generate_encounter(request: EncounterGenerationRequest):
    """
    Generate a balanced D&D 5e encounter based on party composition, desired difficulty, and environment.
    
    This endpoint creates encounters using official D&D 5e encounter balancing rules,
    including XP budgets, encounter multipliers, and creature selection algorithms.
    """
    try:
        # Convert request to domain objects
        party_composition = PartyComposition(
            party_size=request.party_composition.party_size,
            party_level=request.party_composition.party_level,
            characters=request.party_composition.characters or []
        )
        
        # Convert required monsters if provided
        required_monsters: List[EncounterMonster] = []
        if request.required_monsters:
            for rm in request.required_monsters:
                monster_name_key = rm.monster_name.lower()
                if monster_name_key not in encounter_service.monster_database:
                    raise HTTPException(status_code=404, detail=f"Monster not found: {rm.monster_name}")

                monster_obj = encounter_service.monster_database[monster_name_key]
                required_monsters.append(EncounterMonster(monster=monster_obj, count=rm.count))

        # Generate the encounter
        encounter = encounter_service.generate_encounter(
            party_composition=party_composition,
            difficulty=request.difficulty,
            environment=request.environment or Environment.FOREST,
            encounter_theme=request.encounter_theme,
            required_monsters=required_monsters if required_monsters else None,
        )
        
        return _convert_encounter_to_response(encounter)
        
    except Exception as e:
        logger.error(f"Error generating encounter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate encounter: {str(e)}")


@router.post("/assess-difficulty", response_model=DifficultyAssessmentResponse, summary="Assess encounter difficulty")
async def assess_encounter_difficulty(request: DifficultyAssessmentRequest):
    """
    Assess the difficulty of a custom encounter based on party composition and selected monsters.
    
    This endpoint evaluates encounter balance and provides recommendations for adjustment.
    """
    try:
        # Convert party composition
        party_composition = PartyComposition(
            party_size=request.party_composition.party_size,
            party_level=request.party_composition.party_level,
            characters=request.party_composition.characters or []
        )
        
        # Convert monsters to encounter format
        encounter_monsters = []
        for monster_data in request.monsters:
            monster_name = monster_data.get("monster_name", "").lower()
            count = monster_data.get("count", 1)
            
            if monster_name not in encounter_service.monster_database:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Monster not found: {monster_data.get('monster_name', 'unknown')}"
                )
            
            monster = encounter_service.monster_database[monster_name]
            encounter_monsters.append(EncounterMonster(monster=monster, count=count))
        
        # Assess difficulty
        difficulty, analysis = encounter_service.assess_encounter_difficulty(
            encounter_monsters, party_composition
        )
        
        # Generate recommendations
        recommendations = []
        
        if difficulty == EncounterDifficulty.EASY:
            recommendations.append("This encounter may be too easy. Consider adding more monsters or stronger foes.")
        elif difficulty == EncounterDifficulty.DEADLY:
            recommendations.append("This encounter is potentially lethal. Ensure the party is well-prepared.")
            recommendations.append("Consider environmental factors and escape routes for the characters.")
        
        if analysis["monster_count"] > 8:
            recommendations.append("Large numbers of monsters can slow combat. Consider using groups or simplifying.")
        
        if analysis["average_cr"] > party_composition.party_level + 2:
            recommendations.append("Some monsters may be too powerful for this party level.")
        
        return DifficultyAssessmentResponse(
            assessed_difficulty=difficulty.value,
            total_xp=analysis["total_xp"],
            adjusted_xp=analysis["adjusted_xp"],
            encounter_multiplier=analysis["encounter_multiplier"],
            xp_thresholds=analysis["thresholds"],
            monster_count=analysis["monster_count"],
            average_cr=analysis["average_cr"],
            recommendations=recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assessing encounter difficulty: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assess difficulty: {str(e)}")


@router.post("/suggest-monsters", response_model=List[MonsterSuggestionResponse], summary="Suggest monsters for budget")
async def suggest_monsters(request: MonsterSuggestionRequest):
    """
    Suggest monsters that fit within a given XP budget for a specific environment and party level.
    
    Returns a list of monster suggestions with appropriate counts to create balanced encounters.
    """
    try:
        suggestions = encounter_service.suggest_monsters_for_budget(
            xp_budget=request.xp_budget,
            environment=request.environment,
            party_level=request.party_level,
            max_monsters=request.max_monsters
        )
        
        responses = []
        for monster, count in suggestions:
            total_xp = monster.xp_value * count
            multiplier = encounter_service.get_encounter_multiplier(count)
            adjusted_xp = int(total_xp * multiplier)
            
            response = MonsterSuggestionResponse(
                monster=_convert_monster_to_response(monster),
                suggested_count=count,
                total_xp=total_xp,
                adjusted_xp=adjusted_xp
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        logger.error(f"Error suggesting monsters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to suggest monsters: {str(e)}")


@router.get("/monsters", response_model=List[MonsterResponse], summary="List available monsters")
async def list_monsters(
    environment: Optional[Environment] = Query(None, description="Filter by environment"),
    creature_type: Optional[str] = Query(None, description="Filter by creature type"),
    min_cr: Optional[float] = Query(None, description="Minimum challenge rating"),
    max_cr: Optional[float] = Query(None, description="Maximum challenge rating"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results")
):
    """
    List available monsters in the database with optional filtering.
    
    Supports filtering by environment, creature type, and challenge rating range.
    """
    try:
        monsters = list(encounter_service.monster_database.values())
        
        # Apply filters
        if environment:
            monsters = [m for m in monsters if environment in m.environments]
        
        if creature_type:
            monsters = [m for m in monsters if m.creature_type.value.lower() == creature_type.lower()]
        
        if min_cr is not None:
            monsters = [m for m in monsters if m.cr_numeric >= min_cr]
        
        if max_cr is not None:
            monsters = [m for m in monsters if m.cr_numeric <= max_cr]
        
        # Limit results
        monsters = monsters[:limit]
        
        return [_convert_monster_to_response(monster) for monster in monsters]
        
    except Exception as e:
        logger.error(f"Error listing monsters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list monsters: {str(e)}")


@router.get("/monsters/{monster_name}", response_model=MonsterResponse, summary="Get specific monster")
async def get_monster(monster_name: str):
    """
    Get detailed information about a specific monster by name.
    """
    try:
        monster_key = monster_name.lower()
        
        if monster_key not in encounter_service.monster_database:
            raise HTTPException(status_code=404, detail=f"Monster not found: {monster_name}")
        
        monster = encounter_service.monster_database[monster_key]
        return _convert_monster_to_response(monster)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monster {monster_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monster: {str(e)}")


@router.get("/xp-budget", summary="Calculate XP budget for party")
async def calculate_xp_budget(
    party_size: int = Query(..., ge=1, le=8, description="Number of characters"),
    party_level: int = Query(..., ge=1, le=20, description="Average party level"),
    difficulty: EncounterDifficulty = Query(..., description="Desired encounter difficulty")
):
    """
    Calculate the XP budget for an encounter based on party composition and desired difficulty.
    
    Uses official D&D 5e encounter building guidelines.
    """
    try:
        party_composition = PartyComposition(party_size=party_size, party_level=party_level)
        xp_budget = encounter_service.get_xp_budget(party_composition, difficulty)
        
        # Also provide thresholds for all difficulties
        thresholds = {}
        for diff in EncounterDifficulty:
            thresholds[diff.value] = encounter_service.get_xp_budget(party_composition, diff)
        
        return {
            "party_size": party_size,
            "party_level": party_level,
            "requested_difficulty": difficulty.value,
            "xp_budget": xp_budget,
            "all_thresholds": thresholds
        }
        
    except Exception as e:
        logger.error(f"Error calculating XP budget: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate XP budget: {str(e)}")


@router.get("/environments", summary="List available environments")
async def list_environments():
    """
    List all available environment types for encounter generation.
    """
    try:
        environments = [
            {
                "value": env.value,
                "name": env.value.replace("_", " ").title(),
                "description": f"Encounters suitable for {env.value.replace('_', ' ')} environments"
            }
            for env in Environment
        ]
        
        return {"environments": environments}
        
    except Exception as e:
        logger.error(f"Error listing environments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list environments: {str(e)}")


@router.get("/database-summary", summary="Get monster database summary")
async def get_database_summary():
    """
    Get a statistical summary of the monster database including counts by type, environment, and CR.
    """
    try:
        summary = encounter_service.get_monster_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Error getting database summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database summary: {str(e)}")


# Health check endpoint
@router.get("/health", summary="Encounter service health check")
async def health_check():
    """
    Check the health status of the encounter generation service.
    """
    try:
        monster_count = len(encounter_service.monster_database)
        
        return {
            "status": "healthy",
            "service": "encounter_generation",
            "monsters_loaded": monster_count,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Encounter service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "encounter_generation",
            "error": str(e)
        } 