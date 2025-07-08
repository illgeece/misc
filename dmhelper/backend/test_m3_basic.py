"""Basic tests for M3 DiceEngine + inline roll syntax in chat."""

import asyncio
import sys
import traceback
from typing import Dict, Any

# Add the app directory to Python path
sys.path.insert(0, '/Users/miles/Desktop/misc/dmhelper/backend')

try:
    from app.services.dice_engine import DiceEngine, DiceExpression, DiceGroup, DiceRoll, RollType
    from app.services.tool_router import ToolRouter, ToolType, MessageWithTools
    print("✅ Successfully imported M3 services")
except ImportError as e:
    print(f"❌ Failed to import services: {e}")
    sys.exit(1)


def test_dice_engine_basic():
    """Test basic DiceEngine functionality."""
    print("\n🎲 Testing DiceEngine...")
    
    engine = DiceEngine()
    engine.clear_history()
    
    # Test basic roll
    result = engine.execute_roll("1d20+5")
    assert result.is_valid, "1d20+5 should be valid"
    assert 6 <= result.total <= 25, f"Total {result.total} should be between 6-25"
    print(f"  ✅ Basic roll: 1d20+5 = {result.total}")
    
    # Test advantage
    result = engine.execute_roll("1d20adv")
    assert result.is_valid, "1d20adv should be valid"
    assert result.dice_groups[0].roll_type == RollType.ADVANTAGE
    assert len(result.dice_groups[0].rolls) == 2, "Advantage should roll 2 dice"
    print(f"  ✅ Advantage roll: 1d20adv = {result.total}")
    
    # Test invalid expression
    result = engine.execute_roll("invalid")
    assert not result.is_valid, "Invalid expression should fail"
    assert result.error_message is not None, "Should have error message"
    print("  ✅ Invalid expression handling")
    
    # Test history
    assert len(engine.roll_history) == 2, "Should have 2 rolls in history"
    history = engine.get_roll_history(limit=5)
    assert len(history) == 2, "History should return 2 items"
    print("  ✅ Roll history tracking")
    
    # Test deterministic rolls
    seed = "test123"
    result1 = engine.execute_roll("2d6", seed)
    result2 = engine.execute_roll("2d6", seed)
    assert result1.total == result2.total, "Seeded rolls should be deterministic"
    print(f"  ✅ Deterministic rolls: seed '{seed}' = {result1.total}")
    
    print("🎲 DiceEngine tests passed!")


def test_tool_router():
    """Test ToolRouter functionality."""
    print("\n🔧 Testing ToolRouter...")
    
    router = ToolRouter()
    
    # Test dice detection
    detections = router.detect_tools("I attack with 1d20+5")
    dice_detections = [d for d in detections if d.tool_type == ToolType.DICE_ROLL]
    assert len(dice_detections) >= 1, "Should detect dice in attack message"
    print(f"  ✅ Dice detection: found {len(dice_detections)} dice expressions")
    
    # Test ability check suggestion
    detections = router.detect_tools("Make a strength check")
    dice_detections = [d for d in detections if d.tool_type == ToolType.DICE_ROLL]
    assert len(dice_detections) >= 1, "Should suggest dice for ability check"
    detection = dice_detections[0]
    assert detection.parameters.get('expression') == '1d20', "Should suggest 1d20"
    assert detection.parameters.get('suggested') is True, "Should be marked as suggested"
    print("  ✅ Ability check suggestion")
    
    # Test message processing with execution
    processed = router.process_message("I roll 1d20 for initiative", execute_tools=True)
    assert processed.has_tools, "Should detect tools"
    assert len(processed.tool_results) >= 1, "Should execute tools"
    assert processed.tool_results[0].success, "Tool should execute successfully"
    print(f"  ✅ Message processing: {processed.original_message} -> {processed.cleaned_message}")
    
    print("🔧 ToolRouter tests passed!")


def test_integration():
    """Test integration between services."""
    print("\n🔗 Testing Integration...")
    
    engine = DiceEngine()
    router = ToolRouter(engine)
    
    # Test complex message with multiple dice
    message = "I attack with 1d20+5 and deal 2d6+3 damage"
    processed = router.process_message(message, execute_tools=True)
    
    assert processed.has_tools, "Should detect tools"
    dice_results = [r for r in processed.tool_results if r.tool_type == ToolType.DICE_ROLL]
    assert len(dice_results) >= 2, "Should detect multiple dice"
    
    for result in dice_results:
        assert result.success, "All dice rolls should succeed"
        breakdown = result.result
        assert breakdown["valid"], "All rolls should be valid"
        assert breakdown["total"] > 0, "All totals should be positive"
    
    print(f"  ✅ Complex message: detected {len(dice_results)} dice expressions")
    print(f"     Original: {message}")
    print(f"     Cleaned:  {processed.cleaned_message}")
    
    # Test statistics
    stats = engine.get_statistics()
    assert stats["total_rolls"] > 0, "Should have roll statistics"
    print(f"  ✅ Statistics: {stats['total_rolls']} total rolls, avg {stats['average_result']}")
    
    print("🔗 Integration tests passed!")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n⚠️  Testing Edge Cases...")
    
    engine = DiceEngine()
    router = ToolRouter()
    
    # Test large dice count
    result = engine.execute_roll("100d6")
    assert result.is_valid, "100d6 should be valid"
    assert 100 <= result.total <= 600, "Total should be in expected range"
    print("  ✅ Large dice count (100d6)")
    
    # Test too many dice (should fail)
    result = engine.execute_roll("101d6")
    assert not result.is_valid, "101d6 should be invalid"
    print("  ✅ Dice count limit enforcement")
    
    # Test empty message
    detections = router.detect_tools("")
    assert len(detections) == 0, "Empty message should have no detections"
    print("  ✅ Empty message handling")
    
    # Test message with no dice
    detections = router.detect_tools("This is just a regular message")
    dice_detections = [d for d in detections if d.tool_type == ToolType.DICE_ROLL]
    assert len(dice_detections) == 0, "Regular message should have no dice"
    print("  ✅ Non-dice message handling")
    
    print("⚠️  Edge case tests passed!")


def test_dice_mechanics():
    """Test specific D&D dice mechanics."""
    print("\n⚔️  Testing D&D Mechanics...")
    
    engine = DiceEngine()
    
    # Test all standard dice types
    dice_types = [4, 6, 8, 10, 12, 20, 100]
    for sides in dice_types:
        result = engine.execute_roll(f"1d{sides}")
        assert result.is_valid, f"1d{sides} should be valid"
        assert 1 <= result.total <= sides, f"1d{sides} result should be 1-{sides}"
    print(f"  ✅ All standard dice types: {dice_types}")
    
    # Test advantage/disadvantage
    result = engine.execute_roll("1d20dis")
    assert result.is_valid, "Disadvantage should work"
    assert result.dice_groups[0].roll_type == RollType.DISADVANTAGE
    print("  ✅ Disadvantage rolls")
    
    # Test drop lowest (ability score generation)
    result = engine.execute_roll("4d6dl1")
    assert result.is_valid, "4d6dl1 should work"
    group = result.dice_groups[0]
    assert len(group.rolls) == 4, "Should roll 4 dice"
    assert len(group.kept_rolls) == 3, "Should keep 3 dice"
    assert len(group.dropped_rolls) == 1, "Should drop 1 die"
    print(f"  ✅ Ability score generation: 4d6dl1 = {result.total} (kept {[r.result for r in group.kept_rolls]})")
    
    print("⚔️  D&D mechanics tests passed!")


def run_all_tests():
    """Run all tests."""
    print("🎯 Starting M3 DiceEngine + Tools Tests")
    print("=" * 50)
    
    try:
        test_dice_engine_basic()
        test_tool_router()
        test_integration()
        test_edge_cases()
        test_dice_mechanics()
        
        print("\n" + "=" * 50)
        print("🎉 ALL M3 TESTS PASSED!")
        print("\n✨ M3 Implementation Summary:")
        print("- ✅ DiceEngine with full D&D dice support")
        print("- ✅ Advanced mechanics (advantage, drop dice, etc.)")
        print("- ✅ ToolRouter for natural language dice detection")
        print("- ✅ Deterministic rolls with seeds for replay")
        print("- ✅ Roll history and statistics tracking")
        print("- ✅ Comprehensive error handling and validation")
        print("- ✅ Integration with chat system ready")
        print("\n🚀 Ready for M4 (Character templates + creation wizard)!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 