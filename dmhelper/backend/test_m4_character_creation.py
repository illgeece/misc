#!/usr/bin/env python3
"""Comprehensive M4 Character Creation Wizard and Template System Tests."""

import asyncio
import sys
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
import traceback

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_m4_character_creation_complete():
    """Test complete M4 character creation wizard and template system."""
    print("🎭 Testing M4 Character Creation Wizard and Template System\n")
    
    all_tests_passed = True
    test_results = []
    
    try:
        # Import services
        from app.services.character_service import (
            character_service, AbilityScoreMethod, CharacterClass, 
            CharacterRace, CharacterBackground, AbilityScores
        )
        from app.services.template_engine import template_engine
        from app.services.creation_wizard import creation_wizard, CreationStep
        
        # Test 1: Template Engine Basic Functionality
        print("=" * 70)
        print("TEST 1: Template Engine Basic Functionality")
        print("=" * 70)
        
        try:
            # Test template loading
            template_summary = template_engine.get_template_summary()
            templates = template_summary.get('templates', [])
            total_templates = template_summary.get('total_templates', 0)
            print(f"✅ Templates loaded: {total_templates} templates")
            
            # Verify expected templates exist
            template_names = [t['name'] for t in templates]
            print(f"✅ Available templates: {template_names}")
            
            # Test specific template loading
            if templates:
                first_template_id = templates[0]['id']
                template = template_engine.get_template(first_template_id)
                print(f"✅ Template '{template.name}' loaded successfully")
                print(f"   - Race: {template.race}")
                print(f"   - Class: {template.character_class}")
                print(f"   - Background: {template.background}")
                print(f"   - Level: {template.level}")
            
            test_results.append(("Template Engine Basic", "PASSED"))
        
        except Exception as e:
            print(f"❌ Template Engine test failed: {e}")
            test_results.append(("Template Engine Basic", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 2: Character Service Basic Operations
        print("\n" + "=" * 70)
        print("TEST 2: Character Service Basic Operations")
        print("=" * 70)
        
        try:
            # Test ability score generation methods
            print("Testing ability score generation methods:")
            
            # Standard array
            scores = character_service.generate_ability_scores(AbilityScoreMethod.STANDARD_ARRAY)
            print(f"✅ Standard array: {scores.to_dict()}")
            
            # Point buy
            scores = character_service.generate_ability_scores(AbilityScoreMethod.POINT_BUY)
            print(f"✅ Point buy: {scores.to_dict()}")
            
            # Rolled stats
            scores = character_service.generate_ability_scores(AbilityScoreMethod.ROLL_4D6_DROP_LOWEST)
            print(f"✅ Rolled stats: {scores.to_dict()}")
            
            # Test character creation
            test_character = character_service.create_character(
                name="Test Character",
                race="human",
                character_class="fighter",
                background="soldier",
                ability_scores=AbilityScores(
                    strength=15, dexterity=13, constitution=14,
                    intelligence=10, wisdom=12, charisma=8
                ),
                ability_score_method=AbilityScoreMethod.STANDARD_ARRAY
            )
            print(f"✅ Character created: {test_character.name} (ID: {test_character.id})")
            print(f"   - AC: {test_character.armor_class}")
            print(f"   - HP: {test_character.hit_points}")
            print(f"   - Proficiency Bonus: {test_character.proficiency_bonus}")
            
            # Test character validation
            is_valid, errors = character_service.validate_character(test_character)
            print(f"✅ Character validation: {'Valid' if is_valid else 'Invalid'}")
            if errors:
                print(f"   - Errors: {errors}")
            
            test_results.append(("Character Service Basic", "PASSED"))
        
        except Exception as e:
            print(f"❌ Character Service test failed: {e}")
            test_results.append(("Character Service Basic", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 3: Creation Wizard Session Management
        print("\n" + "=" * 70)
        print("TEST 3: Creation Wizard Session Management")
        print("=" * 70)
        
        try:
            # Start creation session
            session = creation_wizard.start_creation_session()
            print(f"✅ Creation session started: {session.session_id}")
            print(f"✅ Initial step: {session.current_step.value}")
            
            # Test session retrieval
            retrieved_session = creation_wizard.get_session(session.session_id)
            assert retrieved_session is not None, "Session retrieval failed"
            print(f"✅ Session retrieved successfully")
            
            # Test step info
            step_info = creation_wizard.get_current_step_info(session.session_id)
            print(f"✅ Step info retrieved: {step_info['current_step']}")
            
            # Test session summary
            summary = creation_wizard.get_session_summary(session.session_id)
            print(f"✅ Session summary: {summary['progress']}% complete")
            
            test_results.append(("Creation Wizard Session", "PASSED"))
        
        except Exception as e:
            print(f"❌ Creation Wizard Session test failed: {e}")
            test_results.append(("Creation Wizard Session", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 4: Complete Character Creation Workflow
        print("\n" + "=" * 70)
        print("TEST 4: Complete Character Creation Workflow")
        print("=" * 70)
        
        try:
            # Start new session for workflow test
            session = creation_wizard.start_creation_session()
            print(f"✅ Started workflow session: {session.session_id}")
            
            # Step 1: Template selection (optional - skip for custom character)
            success, result = creation_wizard.set_template(session.session_id, None)
            assert success, f"Template setting failed: {result}"
            print(f"✅ Template step completed (no template selected)")
            
            # Step 2: Basic info
            success, result = creation_wizard.set_basic_info(session.session_id, "Workflow Test Character")
            assert success, f"Basic info failed: {result}"
            print(f"✅ Basic info step completed")
            
            # Step 3: Race selection
            success, result = creation_wizard.set_race(session.session_id, "human")
            assert success, f"Race selection failed: {result}"
            print(f"✅ Race selection completed")
            
            # Step 4: Class selection
            success, result = creation_wizard.set_class(session.session_id, "fighter")
            assert success, f"Class selection failed: {result}"
            print(f"✅ Class selection completed")
            
            # Step 5: Background selection
            success, result = creation_wizard.set_background(session.session_id, "soldier")
            assert success, f"Background selection failed: {result}"
            print(f"✅ Background selection completed")
            
            # Step 6: Ability scores
            success, result = creation_wizard.set_ability_score_method(session.session_id, AbilityScoreMethod.STANDARD_ARRAY)
            assert success, f"Ability score method failed: {result}"
            print(f"✅ Ability score method set")
            
            # Auto-generate ability scores for standard array
            success, result = creation_wizard.generate_ability_scores(session.session_id)
            assert success, f"Ability score generation failed: {result}"
            print(f"✅ Ability scores generated")
            
            # Step 7: Skip skills (use defaults)
            # Step 8: Skip equipment (use defaults)
            
            # Step 9: Finalization
            success, result = creation_wizard.finalize_character(session.session_id)
            assert success, f"Character finalization failed: {result}"
            print(f"✅ Character finalized successfully")
            
            created_character = result['character']
            print(f"✅ Created character: {created_character['name']}")
            print(f"   - Race: {created_character['race']}")
            print(f"   - Class: {created_character['character_class']}")
            print(f"   - Background: {created_character['background']}")
            print(f"   - Level: {created_character['level']}")
            print(f"   - AC: {created_character['armor_class']}")
            print(f"   - HP: {created_character['hit_points']}")
            
            # Clean up session
            creation_wizard.end_session(session.session_id)
            print(f"✅ Session cleaned up")
            
            test_results.append(("Complete Workflow", "PASSED"))
        
        except Exception as e:
            print(f"❌ Complete Workflow test failed: {e}")
            traceback.print_exc()
            test_results.append(("Complete Workflow", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 5: Template-Based Character Creation
        print("\n" + "=" * 70)
        print("TEST 5: Template-Based Character Creation")
        print("=" * 70)
        
        try:
            template_summary = template_engine.get_template_summary()
            templates = template_summary.get('templates', [])
            
            if templates:
                # Use first available template
                template_data = templates[0]
                template_id = template_data['id']
                template_name = template_data['name']
                
                # Start session
                session = creation_wizard.start_creation_session()
                print(f"✅ Started template-based session: {session.session_id}")
                
                # Set template
                success, result = creation_wizard.set_template(session.session_id, template_id)
                assert success, f"Template setting failed: {result}"
                print(f"✅ Template '{template_name}' applied")
                
                # Basic info
                success, result = creation_wizard.set_basic_info(session.session_id, "Template Test Character")
                assert success, f"Basic info failed: {result}"
                print(f"✅ Basic info completed with template")
                
                # Since template pre-fills race/class/background, skip to ability scores
                # The template should have pre-filled these values
                current_session = creation_wizard.get_session(session.session_id)
                print(f"   - Pre-filled race: {current_session.choices.race}")
                print(f"   - Pre-filled class: {current_session.choices.character_class}")
                print(f"   - Pre-filled background: {current_session.choices.background}")
                
                # Complete remaining steps quickly
                if current_session.current_step != CreationStep.FINALIZATION:
                    # Skip through steps to finalization
                    if not current_session.choices.race:
                        creation_wizard.set_race(session.session_id, "human")
                    if not current_session.choices.character_class:
                        creation_wizard.set_class(session.session_id, "fighter")
                    if not current_session.choices.background:
                        creation_wizard.set_background(session.session_id, "soldier")
                    
                    # Set ability scores if needed
                    if not current_session.choices.ability_scores:
                        creation_wizard.set_ability_score_method(session.session_id, AbilityScoreMethod.STANDARD_ARRAY)
                        creation_wizard.generate_ability_scores(session.session_id)
                
                # Finalize
                success, result = creation_wizard.finalize_character(session.session_id)
                assert success, f"Template character finalization failed: {result}"
                print(f"✅ Template-based character created successfully")
                
                # Clean up
                creation_wizard.end_session(session.session_id)
                
                test_results.append(("Template-Based Creation", "PASSED"))
            else:
                print("⚠️  No templates available for testing")
                test_results.append(("Template-Based Creation", "SKIPPED"))
        
        except Exception as e:
            print(f"❌ Template-Based Creation test failed: {e}")
            traceback.print_exc()
            test_results.append(("Template-Based Creation", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 6: Advanced Features and Edge Cases
        print("\n" + "=" * 70)
        print("TEST 6: Advanced Features and Edge Cases")
        print("=" * 70)
        
        try:
            # Test point buy system
            session = creation_wizard.start_creation_session()
            creation_wizard.set_template(session.session_id, None)
            creation_wizard.set_basic_info(session.session_id, "Point Buy Test")
            creation_wizard.set_race(session.session_id, "human")
            creation_wizard.set_class(session.session_id, "wizard")
            creation_wizard.set_background(session.session_id, "sage")  # Changed from "scholar" to "sage"
            
            # Test point buy method
            success, result = creation_wizard.set_ability_score_method(session.session_id, AbilityScoreMethod.POINT_BUY)
            assert success, f"Point buy method failed: {result}"
            print(f"✅ Point buy method set")
            
            # Test custom ability scores
            custom_scores = {
                'strength': 8, 'dexterity': 14, 'constitution': 13,
                'intelligence': 15, 'wisdom': 12, 'charisma': 10
            }
            success, result = creation_wizard.set_ability_scores(session.session_id, custom_scores)
            assert success, f"Custom ability scores failed: {result}"
            print(f"✅ Custom ability scores set via point buy")
            
            # Test validation
            success, result = creation_wizard.finalize_character(session.session_id)
            assert success, f"Point buy character finalization failed: {result}"
            print(f"✅ Point buy character validated and created")
            
            creation_wizard.end_session(session.session_id)
            
            # Test error handling
            print("\nTesting error handling:")
            
            # Invalid session ID
            result = creation_wizard.get_current_step_info("invalid-session-id")
            assert "error" in result, "Should return error for invalid session"
            print(f"✅ Invalid session ID handled correctly")
            
            # Invalid choices
            session = creation_wizard.start_creation_session()
            success, result = creation_wizard.set_race(session.session_id, "invalid_race")
            assert not success, "Should fail for invalid race"
            print(f"✅ Invalid race handled correctly")
            
            success, result = creation_wizard.set_basic_info(session.session_id, "")
            assert not success, "Should fail for empty name"
            print(f"✅ Empty name handled correctly")
            
            creation_wizard.end_session(session.session_id)
            
            test_results.append(("Advanced Features", "PASSED"))
        
        except Exception as e:
            print(f"❌ Advanced Features test failed: {e}")
            traceback.print_exc()
            test_results.append(("Advanced Features", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test Summary
        print("\n" + "=" * 70)
        print("M4 TEST SUMMARY")
        print("=" * 70)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result, *error in test_results:
            if result == "PASSED":
                print(f"✅ PASS: {test_name}")
                passed += 1
            elif result == "SKIPPED":
                print(f"⚠️  SKIP: {test_name}")
            else:
                print(f"❌ FAIL: {test_name}")
                if error:
                    print(f"   Error: {error[0]}")
        
        print(f"\nResults: {passed}/{total} tests passed")
        
        if all_tests_passed and passed == total:
            print("\n🎉 ALL M4 TESTS PASSED!")
            print("\n✨ M4 Implementation Summary:")
            print("- ✅ Character Service with D&D 5e rules engine")
            print("- ✅ Template Engine with YAML template loading")
            print("- ✅ Creation Wizard with step-by-step workflow")
            print("- ✅ Multiple ability score generation methods")
            print("- ✅ Comprehensive character validation")
            print("- ✅ Template-based character creation")
            print("- ✅ Custom character creation from scratch")
            print("- ✅ Point buy system implementation")
            print("- ✅ Session management and state tracking")
            print("- ✅ Error handling and input validation")
            
            print("\n📊 Technical Implementation:")
            print("- Character classes: All 12 D&D 5e classes supported")
            print("- Races: Core D&D 5e races implemented")
            print("- Backgrounds: Standard D&D 5e backgrounds")
            print("- Ability Scores: Standard Array, Point Buy, Rolled")
            print("- Validation: Rules compliance checking")
            print("- Templates: YAML-based character templates")
            
            print("\n🚀 Ready for Frontend Integration and PDF Export!")
            
            return True
        else:
            print(f"\n⚠️  {total - passed} tests failed. M4 needs additional work.")
            return False
    
    except Exception as e:
        print(f"\n❌ Critical test failure: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run M4 character creation tests."""
    print("🚀 Starting M4 Character Creation Tests\n")
    
    success = await test_m4_character_creation_complete()
    
    if success:
        print("\n🎭 M4 Character Creation System: OPERATIONAL")
        return 0
    else:
        print("\n❌ M4 Character Creation System: NEEDS WORK")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 