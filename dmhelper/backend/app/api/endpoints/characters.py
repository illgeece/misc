"""Character API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.services.character_service import character_service, AbilityScoreMethod
from app.services.template_engine import template_engine
from app.services.creation_wizard import creation_wizard

router = APIRouter()


# Request/Response Models
class AbilityScoresModel(BaseModel):
    """Ability scores model for API."""
    strength: int = Field(..., ge=1, le=30)
    dexterity: int = Field(..., ge=1, le=30)
    constitution: int = Field(..., ge=1, le=30)
    intelligence: int = Field(..., ge=1, le=30)
    wisdom: int = Field(..., ge=1, le=30)
    charisma: int = Field(..., ge=1, le=30)


class CharacterTemplate(BaseModel):
    """Character template model."""
    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0"
    race: str = ""
    character_class: str = Field(..., alias="class")
    background: str = ""
    level: int = Field(1, ge=1, le=20)
    ability_scores: Optional[Dict[str, int]] = None
    equipment: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []

    class Config:
        allow_population_by_field_name = True


class Character(BaseModel):
    """Full character model."""
    id: str
    name: str
    race: str
    character_class: str = Field(..., alias="class")
    background: str
    level: int = Field(1, ge=1, le=20)
    ability_scores: Dict[str, int]
    hit_points: int
    max_hit_points: int
    armor_class: int
    speed: int
    proficiency_bonus: int
    skill_proficiencies: List[str] = []
    equipment: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str
    notes: str = ""

    class Config:
        allow_population_by_field_name = True


class CharacterCreateRequest(BaseModel):
    """Character creation request."""
    name: str = Field(..., min_length=1, max_length=50)
    template_id: Optional[str] = None
    race: Optional[str] = None
    character_class: Optional[str] = Field(None, alias="class")
    background: Optional[str] = None
    ability_score_method: Optional[str] = "standard_array"
    ability_scores: Optional[AbilityScoresModel] = None
    custom_options: Dict[str, Any] = {}

    class Config:
        allow_population_by_field_name = True


class CharacterUpdateRequest(BaseModel):
    """Character update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    hit_points: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    equipment: Optional[List[Dict[str, Any]]] = None


class CreationSessionRequest(BaseModel):
    """Creation session request models."""
    template_id: Optional[str] = None


class BasicInfoRequest(BaseModel):
    """Basic info request."""
    name: str = Field(..., min_length=1, max_length=50)


class RaceRequest(BaseModel):
    """Race selection request."""
    race: str


class ClassRequest(BaseModel):
    """Class selection request."""
    character_class: str = Field(..., alias="class")

    class Config:
        allow_population_by_field_name = True


class BackgroundRequest(BaseModel):
    """Background selection request."""
    background: str


class AbilityScoreMethodRequest(BaseModel):
    """Ability score method request."""
    method: str


class AbilityScoresRequest(BaseModel):
    """Ability scores request."""
    scores: AbilityScoresModel


class SkillsRequest(BaseModel):
    """Skills selection request."""
    skills: List[str]


class EquipmentChoicesRequest(BaseModel):
    """Equipment choices request."""
    choices: Dict[str, str]


# Template Endpoints
@router.get("/templates", response_model=Dict[str, Any])
async def get_character_templates():
    """Get all available character templates."""
    try:
        return template_engine.get_template_summary()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load templates: {str(e)}"
        )


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_character_template(template_id: str):
    """Get a specific character template."""
    template = template_engine.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return template.to_dict()


# Character Management Endpoints
@router.post("/", response_model=Character, status_code=status.HTTP_201_CREATED)
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
    try:
        # Validate ability score method
        try:
            ability_method = AbilityScoreMethod(request.ability_score_method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ability score method: {request.ability_score_method}"
            )
        
        if request.template_id:
            # Create from template
            customizations = {}
            if request.race:
                customizations['race'] = request.race
            if request.character_class:
                customizations['character_class'] = request.character_class
            if request.background:
                customizations['background'] = request.background
            
            custom_ability_scores = None
            if request.ability_scores:
                custom_ability_scores = request.ability_scores.dict()
            
            character = template_engine.create_character_from_template(
                template_id=request.template_id,
                character_name=request.name,
                customizations=customizations,
                ability_score_method=ability_method,
                custom_ability_scores=custom_ability_scores
            )
        else:
            # Create from scratch
            if not all([request.race, request.character_class, request.background]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Race, class, and background are required when not using a template"
                )
            
            # Generate or use provided ability scores
            if request.ability_scores:
                from app.services.character_service import AbilityScores
                ability_scores = AbilityScores(**request.ability_scores.dict())
            else:
                ability_scores = character_service.generate_ability_scores(ability_method)
            
            character = character_service.create_character(
                name=request.name,
                race=request.race,
                character_class=request.character_class,
                background=request.background,
                ability_scores=ability_scores,
                ability_score_method=ability_method
            )
        
        # Convert to response model
        char_dict = character.to_dict()
        char_dict['class'] = char_dict.pop('character_class')
        
        return Character(**char_dict)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create character: {str(e)}"
        )


@router.get("/", response_model=List[Character])
async def get_characters():
    """Get all player characters."""
    try:
        characters = character_service.list_characters()
        
        # Convert to response models
        result = []
        for char in characters:
            char_dict = char.to_dict()
            char_dict['class'] = char_dict.pop('character_class')
            result.append(Character(**char_dict))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load characters: {str(e)}"
        )


@router.get("/{character_id}", response_model=Character)
async def get_character(character_id: str):
    """Get a specific character by ID."""
    character = character_service.load_character(character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    # Convert to response model
    char_dict = character.to_dict()
    char_dict['class'] = char_dict.pop('character_class')
    
    return Character(**char_dict)


@router.put("/{character_id}", response_model=Character)
async def update_character(character_id: str, update_request: CharacterUpdateRequest):
    """Update an existing character."""
    character = character_service.load_character(character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    try:
        # Apply updates
        if update_request.name is not None:
            character.name = update_request.name
        
        if update_request.hit_points is not None:
            character.hit_points = min(update_request.hit_points, character.max_hit_points)
        
        if update_request.notes is not None:
            character.notes = update_request.notes
        
        if update_request.equipment is not None:
            from app.services.character_service import EquipmentItem
            character.equipment = [
                EquipmentItem(**item) for item in update_request.equipment
            ]
            # Recalculate AC after equipment change
            character.armor_class = character.calculate_armor_class()
        
        # Save updated character
        if not character_service.save_character(character):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save character"
            )
        
        # Convert to response model
        char_dict = character.to_dict()
        char_dict['class'] = char_dict.pop('character_class')
        
        return Character(**char_dict)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update character: {str(e)}"
        )


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(character_id: str):
    """Delete a character."""
    character = character_service.load_character(character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    try:
        if not character_service.delete_character(character_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete character"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete character: {str(e)}"
        )


@router.post("/{character_id}/level-up", response_model=Character)
async def level_up_character(character_id: str):
    """Level up a character and recalculate stats."""
    try:
        character = character_service.level_up_character(character_id)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )
        
        # Convert to response model
        char_dict = character.to_dict()
        char_dict['class'] = char_dict.pop('character_class')
        
        return Character(**char_dict)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to level up character: {str(e)}"
        )


@router.get("/{character_id}/summary", response_model=Dict[str, Any])
async def get_character_summary(character_id: str):
    """Get a summary of character stats and abilities."""
    character = character_service.load_character(character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    try:
        return character_service.get_character_summary(character)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get character summary: {str(e)}"
        )


@router.post("/{character_id}/validate", response_model=Dict[str, Any])
async def validate_character(character_id: str):
    """Validate a character against D&D 5e rules."""
    character = character_service.load_character(character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    try:
        is_valid, errors = character_service.validate_character(character)
        return {
            "valid": is_valid,
            "errors": errors,
            "character_id": character_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate character: {str(e)}"
        )


# Character Creation Wizard Endpoints
@router.post("/wizard/start", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def start_creation_session():
    """Start a new character creation session."""
    try:
        session = creation_wizard.start_creation_session()
        return creation_wizard.get_current_step_info(session.session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start creation session: {str(e)}"
        )


@router.get("/wizard/{session_id}", response_model=Dict[str, Any])
async def get_creation_session(session_id: str):
    """Get current state of a creation session."""
    try:
        return creation_wizard.get_current_step_info(session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session info: {str(e)}"
        )


@router.post("/wizard/{session_id}/template")
async def set_creation_template(session_id: str, request: CreationSessionRequest):
    """Set template for character creation."""
    try:
        success, result = creation_wizard.set_template(session_id, request.template_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set template")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set template: {str(e)}"
        )


@router.post("/wizard/{session_id}/basic-info")
async def set_creation_basic_info(session_id: str, request: BasicInfoRequest):
    """Set basic character information."""
    try:
        success, result = creation_wizard.set_basic_info(session_id, request.name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set basic info")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set basic info: {str(e)}"
        )


@router.post("/wizard/{session_id}/race")
async def set_creation_race(session_id: str, request: RaceRequest):
    """Set character race."""
    try:
        success, result = creation_wizard.set_race(session_id, request.race)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set race")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set race: {str(e)}"
        )


@router.post("/wizard/{session_id}/class")
async def set_creation_class(session_id: str, request: ClassRequest):
    """Set character class."""
    try:
        success, result = creation_wizard.set_class(session_id, request.character_class)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set class")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set class: {str(e)}"
        )


@router.post("/wizard/{session_id}/background")
async def set_creation_background(session_id: str, request: BackgroundRequest):
    """Set character background."""
    try:
        success, result = creation_wizard.set_background(session_id, request.background)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set background")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set background: {str(e)}"
        )


@router.post("/wizard/{session_id}/ability-method")
async def set_ability_score_method(session_id: str, request: AbilityScoreMethodRequest):
    """Set ability score generation method."""
    try:
        success, result = creation_wizard.set_ability_score_method(session_id, request.method)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set ability score method")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set ability score method: {str(e)}"
        )


@router.post("/wizard/{session_id}/ability-scores")
async def set_ability_scores(session_id: str, request: AbilityScoresRequest):
    """Set ability scores."""
    try:
        success, result = creation_wizard.set_ability_scores(session_id, request.scores.dict())
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set ability scores")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set ability scores: {str(e)}"
        )


@router.post("/wizard/{session_id}/roll-abilities")
async def roll_ability_scores(session_id: str):
    """Roll new ability scores using dice."""
    try:
        success, result = creation_wizard.roll_ability_scores_with_details(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to roll ability scores")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to roll ability scores: {str(e)}"
        )


@router.post("/wizard/{session_id}/reroll-ability")
async def reroll_single_ability(session_id: str, ability: str = Query(...)):
    """Reroll a single ability score."""
    try:
        success, result = creation_wizard.reroll_single_ability(session_id, ability)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to reroll ability")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reroll ability: {str(e)}"
        )


@router.get("/wizard/{session_id}/dice-options")
async def get_dice_options(session_id: str):
    """Get dice rolling options for ability scores."""
    try:
        return creation_wizard.get_dice_rolling_options(session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dice options: {str(e)}"
        )


@router.post("/wizard/{session_id}/skills")
async def set_creation_skills(session_id: str, request: SkillsRequest):
    """Set skill proficiencies."""
    try:
        success, result = creation_wizard.set_skills(session_id, request.skills)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set skills")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set skills: {str(e)}"
        )


@router.post("/wizard/{session_id}/equipment")
async def set_creation_equipment(session_id: str, request: EquipmentChoicesRequest):
    """Set equipment choices."""
    try:
        success, result = creation_wizard.set_equipment_choices(session_id, request.choices)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to set equipment")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set equipment: {str(e)}"
        )


@router.post("/wizard/{session_id}/finalize")
async def finalize_character_creation(session_id: str):
    """Finalize character creation and create the character."""
    try:
        success, result = creation_wizard.finalize_character(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to finalize character")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize character: {str(e)}"
        )


@router.delete("/wizard/{session_id}")
async def end_creation_session(session_id: str):
    """End a character creation session."""
    try:
        success = creation_wizard.end_session(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        return {"message": "Session ended successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        ) 