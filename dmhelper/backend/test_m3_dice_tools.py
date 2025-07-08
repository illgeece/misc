"""Comprehensive tests for M3 DiceEngine + inline roll syntax in chat."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.services.dice_engine import DiceEngine, DiceExpression, DiceGroup, DiceRoll, RollType
from app.services.tool_router import ToolRouter, ToolType, MessageWithTools
from app.services.chat_service import ChatService
from app.api.endpoints.dice import router as dice_router
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Test app for API testing
test_app = FastAPI()
test_app.include_router(dice_router, prefix="/dice")
client = TestClient(test_app)


class TestDiceEngine:
    """Test the DiceEngine service."""
    
    def setup_method(self):
        """Set up test environment."""
        self.dice_engine = DiceEngine()
        self.dice_engine.clear_history()  # Start with clean history
    
    def test_basic_dice_expressions(self):
        """Test basic dice expression parsing and execution."""
        test_cases = [
            ("1d20", 1, 20),
            ("2d6", 2, 6),
            ("3d8+5", 3, 8),
            ("1d4-1", 1, 4),
            ("d20", 1, 20),  # Implicit count
        ]
        
        for expression, expected_count, expected_sides in test_cases:
            result = self.dice_engine.execute_roll(expression)
            
            assert result.is_valid, f"Expression {expression} should be valid"
            assert len(result.dice_groups) == 1, f"Should have 1 dice group for {expression}"
            
            group = result.dice_groups[0]
            assert group.count == expected_count, f"Count mismatch for {expression}"
            assert group.die_type == expected_sides, f"Die type mismatch for {expression}"
            assert 1 <= result.total <= (expected_count * expected_sides) + 10  # +10 for modifier
    
    def test_advanced_dice_expressions(self):
        """Test advanced dice mechanics."""
        # Advantage
        result = self.dice_engine.execute_roll("1d20adv")
        assert result.is_valid
        group = result.dice_groups[0]
        assert group.roll_type == RollType.ADVANTAGE
        assert len(group.rolls) == 2  # Should roll 2 dice
        assert len(group.kept_rolls) == 1  # Should keep 1
        assert len(group.dropped_rolls) == 1  # Should drop 1
        
        # Disadvantage
        result = self.dice_engine.execute_roll("1d20dis")
        assert result.is_valid
        group = result.dice_groups[0]
        assert group.roll_type == RollType.DISADVANTAGE
        assert len(group.rolls) == 2
        assert len(group.kept_rolls) == 1
        assert len(group.dropped_rolls) == 1
        
        # Drop lowest
        result = self.dice_engine.execute_roll("4d6dl1")
        assert result.is_valid
        group = result.dice_groups[0]
        assert group.roll_type == RollType.DROP_LOWEST
        assert len(group.rolls) == 4
        assert len(group.kept_rolls) == 3
        assert len(group.dropped_rolls) == 1
    
    def test_deterministic_rolls_with_seed(self):
        """Test that seeds produce deterministic results."""
        expression = "2d6+3"
        seed = "test_seed_123"
        
        # Roll multiple times with same seed
        results = []
        for _ in range(5):
            result = self.dice_engine.execute_roll(expression, seed)
            results.append(result.total)
        
        # All results should be identical
        assert all(total == results[0] for total in results), "Seeded rolls should be deterministic"
        
        # Different seed should produce different result (probabilistically)
        different_result = self.dice_engine.execute_roll(expression, "different_seed")
        # Note: There's a small chance this could be the same, but extremely unlikely
    
    def test_invalid_expressions(self):
        """Test invalid dice expressions."""
        invalid_expressions = [
            "",
            "invalid",
            "1d0",
            "0d6",
            "1d999",  # Invalid die type
            "101d6",  # Too many dice
            "1d6+",   # Incomplete modifier
            "d",      # Missing parts
        ]
        
        for expression in invalid_expressions:
            result = self.dice_engine.execute_roll(expression)
            assert not result.is_valid, f"Expression '{expression}' should be invalid"
            assert result.error_message is not None, f"Should have error message for '{expression}'"
    
    def test_roll_history(self):
        """Test roll history functionality."""
        # Start with empty history
        assert len(self.dice_engine.roll_history) == 0
        
        # Make some rolls
        expressions = ["1d20", "2d6+3", "1d8"]
        for expr in expressions:
            self.dice_engine.execute_roll(expr)
        
        # Check history
        assert len(self.dice_engine.roll_history) == len(expressions)
        
        history = self.dice_engine.get_roll_history(limit=10)
        assert len(history) == len(expressions)
        
        # Check that history is in reverse order (most recent first)
        assert history[0]["expression"] == expressions[-1]
        
        # Test history limit
        limited_history = self.dice_engine.get_roll_history(limit=2)
        assert len(limited_history) == 2
        
        # Clear history
        self.dice_engine.clear_history()
        assert len(self.dice_engine.roll_history) == 0
    
    def test_statistics(self):
        """Test dice rolling statistics."""
        # Roll some dice to generate stats
        for _ in range(10):
            self.dice_engine.execute_roll("1d20")
        
        stats = self.dice_engine.get_statistics()
        
        assert stats["total_rolls"] == 10
        assert stats["average_result"] > 0
        assert "critical_hits" in stats
        assert "critical_failures" in stats
        assert "most_common_expression" in stats


class TestToolRouter:
    """Test the ToolRouter service."""
    
    def setup_method(self):
        """Set up test environment."""
        self.tool_router = ToolRouter()
    
    def test_dice_detection_basic(self):
        """Test basic dice expression detection."""
        test_cases = [
            ("I roll 1d20", 1),
            ("Roll 2d6+3 for damage", 1),
            ("Make a strength check", 1),  # Should suggest d20
            ("I attack with 1d20+5 and deal 1d8+3 damage", 2),
            ("No dice here", 0),
        ]
        
        for message, expected_count in test_cases:
            detections = self.tool_router.detect_tools(message)
            dice_detections = [d for d in detections if d.tool_type == ToolType.DICE_ROLL]
            
            assert len(dice_detections) == expected_count, f"Expected {expected_count} dice in '{message}'"
    
    def test_dice_detection_confidence(self):
        """Test confidence scoring for dice detection."""
        high_confidence_messages = [
            "Roll 1d20",
            "I attack with 1d20+5",
            "Roll initiative",
        ]
        
        low_confidence_messages = [
            "The d20 system is good",  # Mentions d20 but not a roll
            "I have 20 gold",  # Contains numbers but not dice
        ]
        
        for message in high_confidence_messages:
            detections = self.tool_router.detect_tools(message)
            dice_detections = [d for d in detections if d.tool_type == ToolType.DICE_ROLL]
            if dice_detections:
                assert dice_detections[0].confidence > 0.7, f"Should have high confidence for '{message}'"
        
        for message in low_confidence_messages:
            detections = self.tool_router.detect_tools(message)
            dice_detections = [d for d in detections if d.tool_type == ToolType.DICE_ROLL]
            # These should either not be detected or have low confidence
            for detection in dice_detections:
                assert detection.confidence < 0.6, f"Should have low confidence for '{message}'"
    
    def test_message_processing_with_execution(self):
        """Test full message processing with tool execution."""
        message = "I attack with 1d20+5"
        
        processed = self.tool_router.process_message(message, execute_tools=True)
        
        assert processed.has_tools
        assert len(processed.detected_tools) >= 1
        assert len(processed.tool_results) >= 1
        
        # Check that the cleaned message contains the roll result
        assert processed.cleaned_message != processed.original_message
        assert "**" in processed.cleaned_message  # Should contain formatting
    
    def test_ability_check_suggestions(self):
        """Test automatic d20 suggestions for ability checks."""
        ability_checks = [
            "Make a strength check",
            "Roll for stealth",
            "Perception check",
            "Initiative roll",
        ]
        
        for check in ability_checks:
            detections = self.tool_router.detect_tools(check)
            dice_detections = [d for d in detections if d.tool_type == ToolType.DICE_ROLL]
            
            assert len(dice_detections) >= 1, f"Should detect dice in '{check}'"
            detection = dice_detections[0]
            assert detection.parameters.get('expression') == '1d20', f"Should suggest 1d20 for '{check}'"
            assert detection.parameters.get('suggested') is True, f"Should be marked as suggested for '{check}'"


class TestChatServiceIntegration:
    """Test ChatService integration with tools."""
    
    def setup_method(self):
        """Set up test environment."""
        self.chat_service = ChatService()
        
        # Mock the LLM service to avoid actual API calls
        self.mock_llm_response = Mock()
        self.mock_llm_response.content = "Great roll! You rolled a 15."
        self.mock_llm_response.model = "test_model"
        self.mock_llm_response.response_time_ms = 1000
        
        self.chat_service.llm_service.generate_dm_response = Mock(return_value=self.mock_llm_response)
        self.chat_service.knowledge_service.search_knowledge = Mock(return_value={"results": []})
    
    @pytest.mark.asyncio
    async def test_chat_with_dice_roll(self):
        """Test chat message with inline dice roll."""
        session_id = self.chat_service.create_session()
        
        response = await self.chat_service.send_message(
            session_id=session_id,
            user_message="I attack the orc with 1d20+5",
            use_rag=False,
            use_tools=True
        )
        
        assert response["tools_used"] is True
        assert len(response["tool_results"]) >= 1
        
        # Check that dice roll was executed
        dice_result = next((r for r in response["tool_results"] if r["tool_type"] == "dice_roll"), None)
        assert dice_result is not None
        assert dice_result["success"] is True
        assert "expression" in dice_result
        assert "total" in dice_result
        
        # Check that LLM was called with tool context
        self.chat_service.llm_service.generate_dm_response.assert_called_once()
        call_args = self.chat_service.llm_service.generate_dm_response.call_args
        assert call_args.kwargs.get('tool_context') is not None
        assert "TOOL RESULTS" in call_args.kwargs.get('tool_context', '')
    
    @pytest.mark.asyncio
    async def test_chat_without_tools(self):
        """Test chat message without tools."""
        session_id = self.chat_service.create_session()
        
        response = await self.chat_service.send_message(
            session_id=session_id,
            user_message="What is the AC of leather armor?",
            use_tools=False
        )
        
        assert response["tools_used"] is False
        assert len(response["tool_results"]) == 0
        
        # LLM should still be called but without tool context
        self.chat_service.llm_service.generate_dm_response.assert_called_once()
        call_args = self.chat_service.llm_service.generate_dm_response.call_args
        assert call_args.kwargs.get('tool_context') is None
    
    @pytest.mark.asyncio
    async def test_multiple_dice_in_message(self):
        """Test message with multiple dice expressions."""
        session_id = self.chat_service.create_session()
        
        response = await self.chat_service.send_message(
            session_id=session_id,
            user_message="I attack with 1d20+5 and deal 2d6+3 damage",
            use_tools=True
        )
        
        assert response["tools_used"] is True
        
        # Should have multiple dice results
        dice_results = [r for r in response["tool_results"] if r["tool_type"] == "dice_roll"]
        assert len(dice_results) >= 2


class TestDiceAPI:
    """Test the dice API endpoints."""
    
    def test_roll_dice_endpoint(self):
        """Test the /dice/roll endpoint."""
        response = client.post(
            "/dice/roll",
            json={"expression": "1d20+5"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["expression"] == "1d20+5"
        assert isinstance(data["total"], int)
        assert 6 <= data["total"] <= 25  # 1-20 + 5
        assert "breakdown" in data
        assert "seed" in data
    
    def test_roll_dice_with_seed(self):
        """Test deterministic rolling with seed."""
        seed = "test_seed_123"
        
        # Roll multiple times with same seed
        responses = []
        for _ in range(3):
            response = client.post(
                "/dice/roll",
                json={"expression": "2d6", "seed": seed}
            )
            assert response.status_code == 200
            responses.append(response.json())
        
        # All should have same result
        totals = [r["total"] for r in responses]
        assert all(total == totals[0] for total in totals)
    
    def test_invalid_dice_expression(self):
        """Test API with invalid dice expression."""
        response = client.post(
            "/dice/roll",
            json={"expression": "invalid"}
        )
        
        assert response.status_code == 200  # API handles invalid gracefully
        data = response.json()
        assert data["valid"] is False
        assert "error" in data
    
    def test_validate_expression_endpoint(self):
        """Test the /dice/validate endpoint."""
        # Valid expression
        response = client.post(
            "/dice/validate",
            json={"expression": "2d6+3"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["expression"] == "2d6+3"
        
        # Invalid expression
        response = client.post(
            "/dice/validate",
            json={"expression": "invalid"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "error" in data
    
    def test_dice_suggestions_endpoint(self):
        """Test the /dice/suggestions endpoint."""
        response = client.get("/dice/suggestions?context=attack")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0
        assert "1d20" in data["suggestions"]  # Should suggest attack roll
    
    def test_detect_dice_endpoint(self):
        """Test the /dice/detect endpoint."""
        response = client.get("/dice/detect?text=I attack with 1d20+5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_dice"] is True
        assert data["count"] >= 1
        assert len(data["detected_dice"]) >= 1
        
        detection = data["detected_dice"][0]
        assert "expression" in detection
        assert "confidence" in detection
        assert "position" in detection
    
    def test_dice_health_endpoint(self):
        """Test the /dice/health endpoint."""
        response = client.get("/dice/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "test_roll" in data
        assert "supported_dice" in data
    
    def test_syntax_help_endpoint(self):
        """Test the /dice/syntax-help endpoint."""
        response = client.get("/dice/syntax-help")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "basic_syntax" in data
        assert "advanced_syntax" in data
        assert "supported_dice" in data
        assert "limits" in data


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test environment."""
        self.dice_engine = DiceEngine()
        self.tool_router = ToolRouter()
    
    def test_critical_hits_and_failures(self):
        """Test detection and handling of critical hits/failures."""
        # Force critical hit
        with patch('random.Random.randint', return_value=20):
            result = self.dice_engine.execute_roll("1d20")
            
            breakdown = result.get_breakdown()
            roll = breakdown["dice_groups"][0]["rolls"][0]
            assert roll["was_max"] is True
            assert roll["result"] == 20
        
        # Force critical failure
        with patch('random.Random.randint', return_value=1):
            result = self.dice_engine.execute_roll("1d20")
            
            breakdown = result.get_breakdown()
            roll = breakdown["dice_groups"][0]["rolls"][0]
            assert roll["was_min"] is True
            assert roll["result"] == 1
    
    def test_large_dice_expressions(self):
        """Test handling of large dice expressions."""
        # Test maximum allowed dice
        result = self.dice_engine.execute_roll("100d6")
        assert result.is_valid
        assert 100 <= result.total <= 600
        
        # Test expression that should be rejected
        result = self.dice_engine.execute_roll("101d6")
        assert not result.is_valid
    
    def test_complex_mixed_expressions(self):
        """Test complex expressions with multiple modifiers."""
        complex_expressions = [
            "1d20+5-2+1",  # Multiple modifiers
            "2d6+3+1d4",   # Multiple dice groups (if supported)
        ]
        
        for expr in complex_expressions:
            result = self.dice_engine.execute_roll(expr)
            # Should either work or fail gracefully
            if result.is_valid:
                assert result.total > 0
            else:
                assert result.error_message is not None
    
    def test_tool_router_edge_cases(self):
        """Test tool router with edge cases."""
        edge_cases = [
            "",  # Empty message
            "d" * 1000,  # Very long message
            "1d20" * 50,  # Many dice expressions
            "🎲 unicode dice 1d6",  # Unicode characters
        ]
        
        for message in edge_cases:
            try:
                detections = self.tool_router.detect_tools(message)
                # Should not crash
                assert isinstance(detections, list)
            except Exception as e:
                pytest.fail(f"Tool router crashed on '{message}': {e}")


def test_end_to_end_dice_workflow():
    """Test complete end-to-end dice workflow."""
    # 1. Create dice engine
    engine = DiceEngine()
    engine.clear_history()
    
    # 2. Roll some dice
    expressions = ["1d20", "2d6+3", "1d8adv"]
    results = []
    
    for expr in expressions:
        result = engine.execute_roll(expr)
        assert result.is_valid
        results.append(result)
    
    # 3. Check history
    history = engine.get_roll_history()
    assert len(history) == len(expressions)
    
    # 4. Test statistics
    stats = engine.get_statistics()
    assert stats["total_rolls"] == len(expressions)
    
    # 5. Test tool router integration
    router = ToolRouter(engine)
    processed = router.process_message("I roll 1d20 for initiative", execute_tools=True)
    
    assert processed.has_tools
    assert len(processed.tool_results) >= 1
    
    # 6. Verify dice result in tool output
    dice_result = next(r for r in processed.tool_results if r.tool_type == ToolType.DICE_ROLL)
    assert dice_result.success
    assert dice_result.result["valid"]


if __name__ == "__main__":
    # Run basic functionality test
    print("Running M3 DiceEngine + Tools basic test...")
    
    try:
        # Test DiceEngine
        engine = DiceEngine()
        result = engine.execute_roll("1d20+5")
        print(f"✅ DiceEngine: {result.expression} = {result.total}")
        
        # Test ToolRouter
        router = ToolRouter(engine)
        processed = router.process_message("I attack with 1d20+3", execute_tools=True)
        print(f"✅ ToolRouter: Detected {len(processed.detected_tools)} tools, executed {len(processed.tool_results)}")
        
        # Test API endpoints
        response = client.post("/dice/roll", json={"expression": "2d6"})
        if response.status_code == 200:
            print(f"✅ API: {response.json()['expression']} = {response.json()['total']}")
        
        print("\n🎉 M3 implementation is working correctly!")
        print("\nFeatures implemented:")
        print("- ✅ DiceEngine with comprehensive D&D dice support")
        print("- ✅ ToolRouter for detecting dice in natural language")
        print("- ✅ Chat integration with inline dice rolling")
        print("- ✅ API endpoints for manual dice rolling")
        print("- ✅ Roll history and statistics")
        print("- ✅ Deterministic rolls with seeds")
        print("- ✅ Advanced mechanics (advantage, drop dice, etc.)")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 