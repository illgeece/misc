"""Character API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class CharacterTemplate(BaseModel):
    """Character template model."""
    name: str
    race: str
    character_class: str
    background: str
    ability_scores: dict
    skills: List[str]
    equipment: List[str]
    description: str = ""


class Character(BaseModel):
    """Full character model."""
    id: str
    name: str
    race: str
    character_class: str
    background: str
    level: int = 1
    ability_scores: dict
    skills: List[str]
    equipment: List[str]
    hit_points: int
    armor_class: int
    proficiency_bonus: int
    description: str = ""
    created_at: str
    updated_at: str


class CharacterCreateRequest(BaseModel):
    """Character creation request."""
    template_name: str = None
    name: str
    race: str = None
    character_class: str = None
    background: str = None
    custom_options: dict = {}


@router.get("/templates", response_model=List[CharacterTemplate])
async def get_character_templates():
    """Get all available character templates."""
    # TODO: Load templates from campaign_root/characters/templates/
    return []


@router.post("/", response_model=Character)
async def create_character(request: CharacterCreateRequest):
    """
    Create a new character from a template or custom options.
    
    This endpoint will:
    1. Load the specified template (if provided)
    2. Apply race, class, and background modifications
    3. Calculate derived stats (HP, AC, proficiency bonus)
    4. Validate the character for rules compliance
    5. Save to campaign_root/characters/pcs/
    """
    # TODO: Implement character creation logic
    character_id = f"char_{request.name.lower().replace(' ', '_')}"
    return Character(
        id=character_id,
        name=request.name,
        race=request.race or "Human",
        character_class=request.character_class or "Fighter",
        background=request.background or "Folk Hero",
        ability_scores={"str": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8},
        skills=["Athletics", "Intimidation"],
        equipment=["Longsword", "Shield", "Chain Mail"],
        hit_points=10,
        armor_class=16,
        proficiency_bonus=2,
        created_at="2025-01-08T10:00:00Z",
        updated_at="2025-01-08T10:00:00Z"
    )


@router.get("/", response_model=List[Character])
async def get_characters():
    """Get all player characters."""
    # TODO: Load characters from campaign_root/characters/pcs/
    return []


@router.get("/{character_id}", response_model=Character)
async def get_character(character_id: str):
    """Get a specific character by ID."""
    # TODO: Load character from file
    raise HTTPException(status_code=404, detail="Character not found")


@router.put("/{character_id}", response_model=Character)
async def update_character(character_id: str, character: Character):
    """Update an existing character."""
    # TODO: Implement character update logic
    raise HTTPException(status_code=404, detail="Character not found")


@router.delete("/{character_id}")
async def delete_character(character_id: str):
    """Delete a character."""
    # TODO: Implement character deletion
    return {"message": f"Character {character_id} deleted"}


@router.post("/{character_id}/level-up")
async def level_up_character(character_id: str):
    """Level up a character and recalculate stats."""
    # TODO: Implement level up logic
    return {"message": f"Character {character_id} leveled up"} 