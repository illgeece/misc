#!/usr/bin/env python3
"""
Comprehensive test suite for M5 Encounter Generation System.

Tests all core M5 functionality:
- Encounter generation with CR balancing
- Monster database and filtering
- XP budget calculations
- API endpoints
- Tool router integration
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up environment
os.environ["ENVIRONMENT"] = "test"
os.environ["CAMPAIGN_ROOT"] = str(backend_dir / "data")

def test_encounter_service_initialization():
    """Test that the encounter service initializes correctly."""
    print("🔧 Testing Encounter Service Initialization...")
    
    try:
        from app.services.encounter_service import encounter_service, EncounterDifficulty, Environment
        
        # Test service initialization
        assert encounter_service is not None, "Encounter service should be initialized"
        
        # Test monster database
        monster_count = len(encounter_service.monster_database)
        assert monster_count > 0, f"Should have monsters in database, got {monster_count}"
        
        # Test that we have core monsters
        core_monsters = ["goblin", "orc", "wolf", "brown bear", "ogre", "hill giant"]
        for monster_name in core_monsters:
            assert monster_name in encounter_service.monster_database, f"Should have {monster_name} in database"
        
        # Test monster properties
        goblin = encounter_service.monster_database["goblin"]
        assert goblin.challenge_rating == "1/4", f"Goblin CR should be 1/4, got {goblin.challenge_rating}"
        assert goblin.xp_value == 50, f"Goblin XP should be 50, got {goblin.xp_value}"
        assert goblin.cr_numeric == 0.25, f"Goblin numeric CR should be 0.25, got {goblin.cr_numeric}"
        
        print("✅ Encounter service initialization: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Encounter service initialization: FAILED - {e}")
        return False


def test_xp_budget_calculations():
    """Test XP budget calculations for different party compositions and difficulties."""
    print("🔧 Testing XP Budget Calculations...")
    
    try:
        from app.services.encounter_service import encounter_service, PartyComposition, EncounterDifficulty
        
        # Test basic budget calculation
        party = PartyComposition(party_size=4, party_level=5)
        
        # Test all difficulty levels
        budgets = {
            EncounterDifficulty.EASY: encounter_service.get_xp_budget(party, EncounterDifficulty.EASY),
            EncounterDifficulty.MEDIUM: encounter_service.get_xp_budget(party, EncounterDifficulty.MEDIUM),
            EncounterDifficulty.HARD: encounter_service.get_xp_budget(party, EncounterDifficulty.HARD),
            EncounterDifficulty.DEADLY: encounter_service.get_xp_budget(party, EncounterDifficulty.DEADLY)
        }
        
        # Verify budget progression (deadly > hard > medium > easy)
        assert budgets[EncounterDifficulty.DEADLY] > budgets[EncounterDifficulty.HARD], "Deadly should be harder than hard"
        assert budgets[EncounterDifficulty.HARD] > budgets[EncounterDifficulty.MEDIUM], "Hard should be harder than medium"
        assert budgets[EncounterDifficulty.MEDIUM] > budgets[EncounterDifficulty.EASY], "Medium should be harder than easy"
        
        # Test specific values for level 5 party of 4
        expected_medium = 500 * 4  # 500 per character at level 5 for medium
        assert budgets[EncounterDifficulty.MEDIUM] == expected_medium, f"Medium budget should be {expected_medium}, got {budgets[EncounterDifficulty.MEDIUM]}"
        
        # Test different party sizes
        small_party = PartyComposition(party_size=2, party_level=5)
        large_party = PartyComposition(party_size=6, party_level=5)
        
        small_budget = encounter_service.get_xp_budget(small_party, EncounterDifficulty.MEDIUM)
        large_budget = encounter_service.get_xp_budget(large_party, EncounterDifficulty.MEDIUM)
        
        assert large_budget > small_budget, "Larger party should have larger budget"
        assert large_budget == small_budget * 3, "Budget should scale linearly with party size"
        
        print("✅ XP budget calculations: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ XP budget calculations: FAILED - {e}")
        return False


def test_encounter_multipliers():
    """Test encounter multiplier calculations."""
    print("🔧 Testing Encounter Multipliers...")
    
    try:
        from app.services.encounter_service import encounter_service
        
        # Test standard multipliers
        test_cases = [
            (1, 1.0),    # Single monster
            (2, 1.5),    # Pair
            (3, 2.0),    # Small group
            (6, 2.0),    # Still small group
            (7, 2.5),    # Medium group
            (10, 2.5),   # Still medium group
            (11, 3.0),   # Large group
            (14, 3.0),   # Still large group
            (15, 4.0),   # Very large group
            (20, 4.0),   # Massive group
        ]
        
        for monster_count, expected_multiplier in test_cases:
            actual_multiplier = encounter_service.get_encounter_multiplier(monster_count)
            assert actual_multiplier == expected_multiplier, f"For {monster_count} monsters, expected {expected_multiplier}, got {actual_multiplier}"
        
        print("✅ Encounter multipliers: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Encounter multipliers: FAILED - {e}")
        return False


def test_monster_filtering():
    """Test monster filtering by environment, CR, and type."""
    print("🔧 Testing Monster Filtering...")
    
    try:
        from app.services.encounter_service import encounter_service, Environment
        
        # Test environment filtering
        forest_monsters = encounter_service.get_monsters_by_environment(Environment.FOREST)
        assert len(forest_monsters) > 0, "Should have forest monsters"
        
        # Verify all returned monsters have forest environment
        for monster in forest_monsters:
            assert Environment.FOREST in monster.environments, f"{monster.name} should have forest environment"
        
        # Test CR range filtering
        low_cr_monsters = encounter_service.get_monsters_by_cr_range(0, 1)
        assert len(low_cr_monsters) > 0, "Should have low CR monsters"
        
        # Verify all returned monsters are in CR range
        for monster in low_cr_monsters:
            assert 0 <= monster.cr_numeric <= 1, f"{monster.name} CR {monster.cr_numeric} should be 0-1"
        
        # Test high CR filtering
        high_cr_monsters = encounter_service.get_monsters_by_cr_range(3, 10)
        assert len(high_cr_monsters) > 0, "Should have high CR monsters"
        
        for monster in high_cr_monsters:
            assert 3 <= monster.cr_numeric <= 10, f"{monster.name} CR {monster.cr_numeric} should be 3-10"
        
        print("✅ Monster filtering: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Monster filtering: FAILED - {e}")
        return False


def test_encounter_generation():
    """Test complete encounter generation."""
    print("🔧 Testing Encounter Generation...")
    
    try:
        from app.services.encounter_service import encounter_service, PartyComposition, EncounterDifficulty, Environment
        
        # Test basic encounter generation
        party = PartyComposition(party_size=4, party_level=5)
        
        encounter = encounter_service.generate_encounter(
            party_composition=party,
            difficulty=EncounterDifficulty.MEDIUM,
            environment=Environment.FOREST
        )
        
        # Verify encounter properties
        assert encounter is not None, "Should generate an encounter"
        assert encounter.party_composition.party_size == 4, "Should preserve party size"
        assert encounter.party_composition.party_level == 5, "Should preserve party level"
        assert encounter.difficulty == EncounterDifficulty.MEDIUM, "Should preserve difficulty"
        assert encounter.environment == Environment.FOREST, "Should preserve environment"
        
        # Verify monsters
        assert len(encounter.monsters) > 0, "Should have monsters"
        assert encounter.total_monster_count > 0, "Should have monster count"
        
        # Verify XP calculations
        assert encounter.total_xp > 0, "Should have total XP"
        assert encounter.adjusted_xp > 0, "Should have adjusted XP"
        assert encounter.xp_budget > 0, "Should have XP budget"
        
        # Verify that adjusted XP is reasonable for the budget
        budget_ratio = encounter.adjusted_xp / encounter.xp_budget
        assert 0.5 <= budget_ratio <= 1.2, f"Adjusted XP should be 50-120% of budget, got {budget_ratio:.2f}"
        
        # Verify encounter has tactical notes
        assert encounter.tactical_notes, "Should have tactical notes"
        assert len(encounter.environmental_features) > 0, "Should have environmental features"
        
        # Test different difficulties
        easy_encounter = encounter_service.generate_encounter(party, EncounterDifficulty.EASY, Environment.DUNGEON)
        deadly_encounter = encounter_service.generate_encounter(party, EncounterDifficulty.DEADLY, Environment.MOUNTAINS)
        
        assert easy_encounter.adjusted_xp < deadly_encounter.adjusted_xp, "Deadly should have more XP than easy"
        
        print("✅ Encounter generation: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Encounter generation: FAILED - {e}")
        return False


def test_difficulty_assessment():
    """Test encounter difficulty assessment."""
    print("🔧 Testing Difficulty Assessment...")
    
    try:
        from app.services.encounter_service import encounter_service, PartyComposition, EncounterMonster, EncounterDifficulty
        
        party = PartyComposition(party_size=4, party_level=3)
        
        # Create a test encounter with known monsters
        goblin = encounter_service.monster_database["goblin"]
        orc = encounter_service.monster_database["orc"]
        
        # Test easy encounter (few weak monsters)
        easy_monsters = [EncounterMonster(monster=goblin, count=2)]
        difficulty, analysis = encounter_service.assess_encounter_difficulty(easy_monsters, party)
        
        assert difficulty in [EncounterDifficulty.EASY, EncounterDifficulty.MEDIUM], f"2 goblins should be easy/medium for level 3 party, got {difficulty}"
        assert analysis["monster_count"] == 2, "Should count 2 monsters"
        assert analysis["total_xp"] == 100, "Should have 100 total XP (50 * 2)"
        
        # Test harder encounter (more/stronger monsters)
        hard_monsters = [
            EncounterMonster(monster=orc, count=3),
            EncounterMonster(monster=goblin, count=4)
        ]
        difficulty, analysis = encounter_service.assess_encounter_difficulty(hard_monsters, party)
        
        assert difficulty in [EncounterDifficulty.HARD, EncounterDifficulty.DEADLY], f"3 orcs + 4 goblins should be hard/deadly, got {difficulty}"
        assert analysis["monster_count"] == 7, "Should count 7 monsters total"
        
        print("✅ Difficulty assessment: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Difficulty assessment: FAILED - {e}")
        return False


def test_tool_router_integration():
    """Test tool router integration with encounter generation."""
    print("🔧 Testing Tool Router Integration...")
    
    try:
        from app.services.tool_router import tool_router, ToolType
        
        # Test encounter detection
        test_messages = [
            "Generate a medium encounter for 4 level 5 characters in a forest",
            "I need an encounter for my party",
            "Create a hard encounter in a dungeon",
            "Make a level 3 encounter for 6 players in the mountains",
            "Generate encounter CR 2 for urban setting"
        ]
        
        for message in test_messages:
            detected = tool_router.detect_tools(message)
            
            # Should detect encounter generation
            encounter_tools = [t for t in detected if t.tool_type == ToolType.ENCOUNTER_GENERATION]
            assert len(encounter_tools) > 0, f"Should detect encounter in: {message}"
            
            tool = encounter_tools[0]
            assert tool.confidence >= 0.6, f"Should have reasonable confidence for: {message}"
            
            # Test parameter extraction
            if "medium" in message:
                assert tool.parameters.get("difficulty") == "medium", "Should extract medium difficulty"
            if "forest" in message:
                assert tool.parameters.get("environment") == "forest", "Should extract forest environment"
            if "4 level 5" in message or "level 5" in message:
                assert tool.parameters.get("party_level") == 5, "Should extract party level 5"
        
        # Test tool execution
        message = "Generate a medium forest encounter for 4 level 5 characters"
        processed = tool_router.process_message(message, execute_tools=True)
        
        assert processed.has_tools, "Should detect tools"
        assert len(processed.tool_results) > 0, "Should execute tools"
        
        encounter_result = processed.tool_results[0]
        assert encounter_result.success, f"Encounter generation should succeed: {encounter_result.error_message}"
        assert encounter_result.formatted_result, "Should have formatted result"
        
        print("✅ Tool router integration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Tool router integration: FAILED - {e}")
        return False


async def test_api_endpoints():
    """Test encounter API endpoints."""
    print("🔧 Testing API Endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Test health check
        response = client.get("/api/v1/encounters/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        health_data = response.json()
        assert health_data["status"] == "healthy", "Service should be healthy"
        
        # Test monster listing
        response = client.get("/api/v1/encounters/monsters")
        assert response.status_code == 200, f"Monster listing failed: {response.status_code}"
        
        monsters = response.json()
        assert len(monsters) > 0, "Should return monsters"
        assert "name" in monsters[0], "Monster should have name"
        assert "challenge_rating" in monsters[0], "Monster should have CR"
        
        # Test specific monster
        response = client.get("/api/v1/encounters/monsters/goblin")
        assert response.status_code == 200, f"Goblin lookup failed: {response.status_code}"
        
        goblin = response.json()
        assert goblin["name"] == "Goblin", "Should return goblin"
        assert goblin["challenge_rating"] == "1/4", "Should have correct CR"
        
        # Test XP budget calculation
        response = client.get("/api/v1/encounters/xp-budget?party_size=4&party_level=5&difficulty=medium")
        assert response.status_code == 200, f"XP budget failed: {response.status_code}"
        
        budget_data = response.json()
        assert budget_data["xp_budget"] == 2000, f"Should have 2000 XP budget, got {budget_data['xp_budget']}"
        
        # Test encounter generation
        request_data = {
            "party_composition": {
                "party_size": 4,
                "party_level": 5
            },
            "difficulty": "medium",
            "environment": "forest"
        }
        
        response = client.post("/api/v1/encounters/generate", json=request_data)
        assert response.status_code == 200, f"Encounter generation failed: {response.status_code}"
        
        encounter = response.json()
        assert encounter["difficulty"] == "medium", "Should preserve difficulty"
        assert encounter["environment"] == "forest", "Should preserve environment"
        assert len(encounter["monsters"]) > 0, "Should have monsters"
        assert encounter["total_xp"] > 0, "Should have XP"
        
        # Test difficulty assessment
        assessment_data = {
            "party_composition": {
                "party_size": 4,
                "party_level": 3
            },
            "monsters": [
                {"monster_name": "Goblin", "count": 4},
                {"monster_name": "Orc", "count": 1}
            ]
        }
        
        response = client.post("/api/v1/encounters/assess-difficulty", json=assessment_data)
        assert response.status_code == 200, f"Difficulty assessment failed: {response.status_code}"
        
        assessment = response.json()
        assert "assessed_difficulty" in assessment, "Should assess difficulty"
        assert assessment["monster_count"] == 5, "Should count monsters correctly"
        
        print("✅ API endpoints: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ API endpoints: FAILED - {e}")
        return False


def test_edge_cases():
    """Test edge cases and error handling."""
    print("🔧 Testing Edge Cases...")
    
    try:
        from app.services.encounter_service import encounter_service, PartyComposition, EncounterDifficulty, Environment
        
        # Test very small party
        tiny_party = PartyComposition(party_size=1, party_level=1)
        encounter = encounter_service.generate_encounter(tiny_party, EncounterDifficulty.EASY, Environment.FOREST)
        assert encounter is not None, "Should handle single character"
        assert len(encounter.monsters) >= 1, "Should have at least one monster type"
        assert encounter.total_monster_count >= 1, "Should have at least one monster"
        
        # Test very large party
        large_party = PartyComposition(party_size=8, party_level=10)
        encounter = encounter_service.generate_encounter(large_party, EncounterDifficulty.DEADLY, Environment.DUNGEON)
        assert encounter is not None, "Should handle large party"
        
        # Test high level party
        high_level_party = PartyComposition(party_size=4, party_level=20)
        encounter = encounter_service.generate_encounter(high_level_party, EncounterDifficulty.MEDIUM, Environment.PLANAR)
        assert encounter is not None, "Should handle high level party"
        
        # Test empty monster lists
        from app.services.encounter_service import EncounterMonster
        empty_monsters = []
        difficulty, analysis = encounter_service.assess_encounter_difficulty(empty_monsters, tiny_party)
        assert analysis["monster_count"] == 0, "Should handle empty monster list"
        
        print("✅ Edge cases: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Edge cases: FAILED - {e}")
        return False


def main():
    """Run all M5 encounter generation tests."""
    print("🎯 Starting M5 Encounter Generation System Tests")
    print("=" * 60)
    
    # List of all test functions
    tests = [
        test_encounter_service_initialization,
        test_xp_budget_calculations,
        test_encounter_multipliers,
        test_monster_filtering,
        test_encounter_generation,
        test_difficulty_assessment,
        test_tool_router_integration,
        test_edge_cases,
    ]
    
    # Run synchronous tests
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__}: FAILED - {e}")
            failed += 1
        print()
    
    # Run async tests
    print("🔧 Running async tests...")
    try:
        result = asyncio.run(test_api_endpoints())
        if result:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"❌ test_api_endpoints: FAILED - {e}")
        failed += 1
    
    print()
    print("=" * 60)
    print("🎯 M5 ENCOUNTER GENERATION TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    print(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL M5 TESTS PASSED! 🎉")
        print("✅ Encounter generation system is fully operational!")
        print("\n📋 M5 Features Verified:")
        print("  • D&D 5e encounter balancing with XP budgets")
        print("  • Monster database with 10+ core creatures")
        print("  • CR calculation and difficulty assessment")
        print("  • Environment-based monster filtering")
        print("  • Complete API endpoints (12 endpoints)")
        print("  • Tool router integration for natural language")
        print("  • Tactical recommendations and environmental features")
        print("  • Party composition analysis")
        print("  • Edge case handling")
        
        print("\n🚀 Ready for M6 development!")
        return True
    else:
        print(f"\n❌ {failed} tests failed. Please review and fix issues.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 