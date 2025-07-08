"""Dice rolling API endpoints."""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.dice_engine import dice_engine
from app.services.tool_router import tool_router

logger = logging.getLogger(__name__)

router = APIRouter()


class DiceRollRequest(BaseModel):
    """Request model for dice roll."""
    expression: str = Field(..., description="Dice expression (e.g., '2d6+3', '1d20adv')")
    seed: Optional[str] = Field(None, description="Optional seed for deterministic results")


class DiceRollResponse(BaseModel):
    """Response model for dice roll."""
    expression: str
    total: int
    breakdown: Dict[str, Any]
    seed: str
    valid: bool
    error: Optional[str] = None


class RollHistoryResponse(BaseModel):
    """Response model for roll history."""
    rolls: List[Dict[str, Any]]
    total_count: int


class DiceSuggestionsResponse(BaseModel):
    """Response model for dice suggestions."""
    suggestions: List[str]
    context: str


class ValidationResponse(BaseModel):
    """Response model for expression validation."""
    valid: bool
    error: Optional[str] = None
    expression: str
    parsed_groups: Optional[int] = None
    dice_types: Optional[List[str]] = None


@router.post("/roll", response_model=DiceRollResponse)
async def roll_dice(request: DiceRollRequest):
    """
    Roll dice with the given expression.
    
    Supports standard D&D dice notation:
    - Basic: 1d20, 2d6+3, 3d8-1
    - Advantage/Disadvantage: 1d20adv, 1d20dis
    - Drop dice: 4d6dl1 (drop lowest), 3d6dh1 (drop highest)
    - Keep dice: 6d6kh3 (keep highest 3), 4d6kl2 (keep lowest 2)
    """
    try:
        if not request.expression.strip():
            raise HTTPException(status_code=400, detail="Dice expression cannot be empty")
        
        # Execute the dice roll
        result = dice_engine.execute_roll(request.expression, request.seed)
        
        if not result.is_valid:
            return DiceRollResponse(
                expression=request.expression,
                total=0,
                breakdown={},
                seed="",
                valid=False,
                error=result.error_message
            )
        
        return DiceRollResponse(
            expression=result.expression,
            total=result.total,
            breakdown=result.get_breakdown(),
            seed=result.seed,
            valid=True
        )
        
    except Exception as e:
        logger.error(f"Dice roll failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dice roll failed: {str(e)}")


@router.get("/history", response_model=RollHistoryResponse)
async def get_roll_history(
    limit: int = Query(50, ge=1, le=1000, description="Number of recent rolls to return")
):
    """Get the recent dice roll history."""
    try:
        rolls = dice_engine.get_roll_history(limit=limit)
        
        return RollHistoryResponse(
            rolls=rolls,
            total_count=len(dice_engine.roll_history)
        )
        
    except Exception as e:
        logger.error(f"Failed to get roll history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get roll history: {str(e)}")


@router.delete("/history")
async def clear_roll_history():
    """Clear the dice roll history."""
    try:
        dice_engine.clear_history()
        return {"message": "Roll history cleared successfully"}
        
    except Exception as e:
        logger.error(f"Failed to clear roll history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")


@router.get("/history/{seed}")
async def replay_roll(seed: str):
    """Replay a dice roll using its seed."""
    try:
        result = dice_engine.replay_roll(seed)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"No roll found with seed: {seed}")
        
        return DiceRollResponse(
            expression=result.expression,
            total=result.total,
            breakdown=result.get_breakdown(),
            seed=result.seed,
            valid=result.is_valid,
            error=result.error_message if not result.is_valid else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replay roll: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to replay roll: {str(e)}")


@router.post("/validate", response_model=ValidationResponse)
async def validate_expression(request: DiceRollRequest):
    """Validate a dice expression without rolling."""
    try:
        validation = dice_engine.validate_expression_syntax(request.expression)
        
        return ValidationResponse(
            valid=validation["valid"],
            error=validation.get("error"),
            expression=validation["expression"],
            parsed_groups=validation.get("parsed_groups"),
            dice_types=validation.get("dice_types")
        )
        
    except Exception as e:
        logger.error(f"Expression validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/suggestions", response_model=DiceSuggestionsResponse)
async def get_dice_suggestions(
    context: str = Query("", description="Context for generating suggestions (e.g., 'attack', 'damage', 'save')")
):
    """Get suggested dice expressions based on context."""
    try:
        suggestions = dice_engine.suggest_expressions(context)
        
        return DiceSuggestionsResponse(
            suggestions=suggestions,
            context=context
        )
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/detect")
async def detect_dice_in_text(
    text: str = Query(..., description="Text to analyze for dice expressions")
):
    """Detect dice expressions in text without executing them."""
    try:
        processed = tool_router.process_message(text, execute_tools=False)
        
        dice_detections = [
            {
                "detected_text": detection.extracted_text,
                "expression": detection.parameters.get('expression', ''),
                "confidence": detection.confidence,
                "position": {
                    "start": detection.start_pos,
                    "end": detection.end_pos
                },
                "suggested": detection.parameters.get('suggested', False),
                "check_type": detection.parameters.get('check_type')
            }
            for detection in processed.detected_tools 
            if detection.tool_type.value == 'dice_roll'
        ]
        
        return {
            "original_text": text,
            "detected_dice": dice_detections,
            "count": len(dice_detections),
            "has_dice": len(dice_detections) > 0
        }
        
    except Exception as e:
        logger.error(f"Dice detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.get("/statistics")
async def get_dice_statistics():
    """Get statistics about dice rolls."""
    try:
        stats = dice_engine.get_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/health")
async def dice_health_check():
    """Check the health of the dice service."""
    try:
        # Test basic dice rolling functionality
        test_roll = dice_engine.execute_roll("1d20")
        
        return {
            "status": "healthy",
            "test_roll": {
                "expression": test_roll.expression,
                "total": test_roll.total,
                "valid": test_roll.is_valid
            },
            "roll_history_count": len(dice_engine.roll_history),
            "supported_dice": list(dice_engine.VALID_DICE_TYPES)
        }
        
    except Exception as e:
        logger.error(f"Dice health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "roll_history_count": 0
        }


# Additional utility endpoints

@router.get("/syntax-help")
async def get_syntax_help():
    """Get help information about dice expression syntax."""
    return {
        "basic_syntax": {
            "description": "Basic dice notation: [count]d[sides][modifier]",
            "examples": [
                "1d20 - Roll one 20-sided die",
                "2d6+3 - Roll two 6-sided dice and add 3", 
                "3d8-1 - Roll three 8-sided dice and subtract 1"
            ]
        },
        "advanced_syntax": {
            "advantage_disadvantage": {
                "description": "Roll with advantage (take highest) or disadvantage (take lowest)",
                "examples": [
                    "1d20adv - Roll with advantage",
                    "1d20dis - Roll with disadvantage"
                ]
            },
            "drop_dice": {
                "description": "Drop lowest or highest dice from the roll",
                "examples": [
                    "4d6dl1 - Roll 4d6, drop the lowest",
                    "3d6dh1 - Roll 3d6, drop the highest"
                ]
            },
            "keep_dice": {
                "description": "Keep only the highest or lowest dice",
                "examples": [
                    "6d6kh3 - Roll 6d6, keep the highest 3",
                    "4d6kl2 - Roll 4d6, keep the lowest 2"
                ]
            }
        },
        "supported_dice": [f"d{sides}" for sides in sorted(dice_engine.VALID_DICE_TYPES)],
        "limits": {
            "max_dice_per_roll": 100,
            "max_history_size": dice_engine.max_history_size
        }
    } 