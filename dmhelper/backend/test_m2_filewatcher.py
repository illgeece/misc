#!/usr/bin/env python3
"""Comprehensive M2 File Watcher and Auto-Indexing Tests."""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_m2_file_watcher_functionality():
    """Test complete M2 file watcher and auto-indexing functionality."""
    print("🔥 Testing M2 File Watcher and Auto-Indexing\n")
    
    all_tests_passed = True
    test_results = []
    
    try:
        # Import services
        from app.services.file_watcher import file_watcher_service
        from app.services.background_tasks import background_task_manager
        from app.services.knowledge_service import knowledge_service
        from app.services.vector_store import vector_store
        from app.core.config import get_settings
        
        settings = get_settings()
        
        # Test 1: Background Task Manager Health
        print("=" * 60)
        print("TEST 1: Background Task Manager")
        print("=" * 60)
        
        try:
            # Check initial status
            status = background_task_manager.get_status()
            health = background_task_manager.health_check()
            
            print(f"✅ Background Task Manager Status: {status['is_running']}")
            print(f"✅ Background Task Manager Health: {health['status']}")
            
            test_results.append(("Background Task Manager", "PASSED"))
        
        except Exception as e:
            print(f"❌ Background Task Manager test failed: {e}")
            test_results.append(("Background Task Manager", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 2: File Watcher Service Health
        print("\n" + "=" * 60)
        print("TEST 2: File Watcher Service")
        print("=" * 60)
        
        try:
            # Check file watcher status
            watcher_status = file_watcher_service.get_status()
            watcher_health = file_watcher_service.health_check()
            
            print(f"✅ File Watcher Running: {watcher_status['is_running']}")
            print(f"✅ File Watcher Health: {watcher_health['status']}")
            print(f"✅ Watch Path: {watcher_status['watch_path']}")
            print(f"✅ Queue Size: {watcher_status['queue_size']}")
            
            test_results.append(("File Watcher Service", "PASSED"))
        
        except Exception as e:
            print(f"❌ File Watcher Service test failed: {e}")
            test_results.append(("File Watcher Service", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 3: Start File Watcher
        print("\n" + "=" * 60)
        print("TEST 3: Start File Watcher")
        print("=" * 60)
        
        try:
            # Stop watcher if running
            await file_watcher_service.stop_watching()
            time.sleep(0.5)
            
            # Start file watcher
            start_result = await file_watcher_service.start_watching()
            print(f"✅ File Watcher Start Result: {start_result['status']}")
            
            # Wait for watcher to initialize
            await asyncio.sleep(1.0)
            
            # Check status
            status = file_watcher_service.get_status()
            print(f"✅ File Watcher Active: {status['is_running']}")
            print(f"✅ Observer Alive: {status['observer_alive']}")
            print(f"✅ Processing Task Running: {status['processing_task_running']}")
            
            test_results.append(("Start File Watcher", "PASSED"))
        
        except Exception as e:
            print(f"❌ Start File Watcher test failed: {e}")
            test_results.append(("Start File Watcher", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 4: File Creation Detection
        print("\n" + "=" * 60)
        print("TEST 4: File Creation Detection")
        print("=" * 60)
        
        try:
            # Clear existing knowledge base
            await knowledge_service.clear_knowledge_base()
            await asyncio.sleep(0.5)
            
            # Create a temporary test file in the campaign directory
            campaign_dir = Path(settings.campaign_root_dir)
            campaign_dir.mkdir(parents=True, exist_ok=True)
            
            test_file = campaign_dir / "test_auto_index.md"
            test_content = """
# Test Auto-Indexing Document

This is a test document for auto-indexing functionality.

## Rules
- Test rule 1: This is an automatically indexed rule
- Test rule 2: This rule should appear in search results

## Lore
The kingdom of Testlandia has magical auto-indexing capabilities.
"""
            
            # Write test file
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            print(f"✅ Created test file: {test_file}")
            
            # Wait for file watcher to detect and process
            print("⏳ Waiting for file watcher to process...")
            await asyncio.sleep(3.0)
            
            # Check if file was indexed
            stats = knowledge_service.get_knowledge_stats()
            sources = knowledge_service.get_source_files()
            
            print(f"✅ Total chunks in knowledge base: {stats['total_chunks']}")
            print(f"✅ Source files indexed: {len(sources)}")
            
            # Search for content from the test file
            search_result = await knowledge_service.search_knowledge(
                "auto-indexing rule",
                limit=5,
                min_score=0.1
            )
            
            print(f"✅ Search results found: {search_result['total_results']}")
            
            if search_result['total_results'] > 0:
                print("✅ File was automatically indexed and is searchable!")
                test_results.append(("File Creation Detection", "PASSED"))
            else:
                print("❌ File was not automatically indexed")
                test_results.append(("File Creation Detection", "FAILED", "File not indexed"))
                all_tests_passed = False
        
        except Exception as e:
            print(f"❌ File Creation Detection test failed: {e}")
            test_results.append(("File Creation Detection", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 5: File Modification Detection
        print("\n" + "=" * 60)
        print("TEST 5: File Modification Detection")
        print("=" * 60)
        
        try:
            # Modify the test file
            modified_content = test_content + """

## Updated Content
This content was added to test file modification detection.
The magic sword of Testlandia can auto-update indexes.
"""
            
            with open(test_file, 'w') as f:
                f.write(modified_content)
            
            print(f"✅ Modified test file: {test_file}")
            
            # Wait for file watcher to detect and process
            print("⏳ Waiting for file watcher to process modification...")
            await asyncio.sleep(3.0)
            
            # Search for the new content
            search_result = await knowledge_service.search_knowledge(
                "magic sword Testlandia",
                limit=5,
                min_score=0.1
            )
            
            print(f"✅ Search results for new content: {search_result['total_results']}")
            
            if search_result['total_results'] > 0:
                print("✅ File modification was automatically detected and indexed!")
                test_results.append(("File Modification Detection", "PASSED"))
            else:
                print("❌ File modification was not detected")
                test_results.append(("File Modification Detection", "FAILED", "Modification not detected"))
                all_tests_passed = False
        
        except Exception as e:
            print(f"❌ File Modification Detection test failed: {e}")
            test_results.append(("File Modification Detection", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 6: File Deletion Detection
        print("\n" + "=" * 60)
        print("TEST 6: File Deletion Detection")
        print("=" * 60)
        
        try:
            # Check chunks before deletion
            chunks_before = vector_store.get_chunks_by_source(str(test_file))
            print(f"✅ Chunks before deletion: {len(chunks_before)}")
            
            # Delete the test file
            os.remove(test_file)
            print(f"✅ Deleted test file: {test_file}")
            
            # Wait for file watcher to detect and process
            print("⏳ Waiting for file watcher to process deletion...")
            await asyncio.sleep(3.0)
            
            # Check if chunks were removed
            chunks_after = vector_store.get_chunks_by_source(str(test_file))
            print(f"✅ Chunks after deletion: {len(chunks_after)}")
            
            if len(chunks_after) == 0 and len(chunks_before) > 0:
                print("✅ File deletion was automatically detected and chunks removed!")
                test_results.append(("File Deletion Detection", "PASSED"))
            else:
                print("❌ File deletion was not properly detected")
                test_results.append(("File Deletion Detection", "FAILED", "Deletion not processed"))
                all_tests_passed = False
        
        except Exception as e:
            print(f"❌ File Deletion Detection test failed: {e}")
            test_results.append(("File Deletion Detection", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 7: Manual Refresh Functionality
        print("\n" + "=" * 60)
        print("TEST 7: Manual Refresh Functionality")
        print("=" * 60)
        
        try:
            # Create some test files
            test_files = []
            for i in range(3):
                test_file = campaign_dir / f"manual_test_{i}.md"
                with open(test_file, 'w') as f:
                    f.write(f"# Manual Test {i}\nThis is test file {i} for manual refresh testing.")
                test_files.append(test_file)
            
            print(f"✅ Created {len(test_files)} test files")
            
            # Trigger manual refresh
            refresh_result = await background_task_manager.trigger_manual_refresh()
            print(f"✅ Manual refresh result: {refresh_result['status']}")
            
            if refresh_result['status'] == 'success':
                refresh_data = refresh_result['refresh_result']
                print(f"✅ Files refreshed: {refresh_data.get('refreshed_files', 0)}")
                print(f"✅ Files skipped: {refresh_data.get('skipped_files', 0)}")
                print(f"✅ Errors: {refresh_data.get('errors', 0)}")
                test_results.append(("Manual Refresh", "PASSED"))
            else:
                print("❌ Manual refresh failed")
                test_results.append(("Manual Refresh", "FAILED", refresh_result.get('message', 'Unknown error')))
                all_tests_passed = False
            
            # Clean up test files
            for test_file in test_files:
                if test_file.exists():
                    os.remove(test_file)
        
        except Exception as e:
            print(f"❌ Manual Refresh test failed: {e}")
            test_results.append(("Manual Refresh", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 8: Background Task Manager Integration
        print("\n" + "=" * 60)
        print("TEST 8: Background Task Manager Integration")
        print("=" * 60)
        
        try:
            # Test restart functionality
            restart_result = await background_task_manager.restart_file_watcher()
            print(f"✅ File watcher restart result: {restart_result['status']}")
            
            # Wait for restart to complete
            await asyncio.sleep(1.0)
            
            # Check status after restart
            status = background_task_manager.get_status()
            print(f"✅ Background manager running: {status['is_running']}")
            print(f"✅ Services count: {status['total_services']}")
            
            test_results.append(("Background Task Integration", "PASSED"))
        
        except Exception as e:
            print(f"❌ Background Task Manager Integration test failed: {e}")
            test_results.append(("Background Task Integration", "FAILED", str(e)))
            all_tests_passed = False
        
        # Test 9: File Watcher Statistics
        print("\n" + "=" * 60)
        print("TEST 9: File Watcher Statistics")
        print("=" * 60)
        
        try:
            status = file_watcher_service.get_status()
            stats = status.get('stats', {})
            
            print(f"✅ Files created: {stats.get('files_created', 0)}")
            print(f"✅ Files modified: {stats.get('files_modified', 0)}")
            print(f"✅ Files deleted: {stats.get('files_deleted', 0)}")
            print(f"✅ Index operations: {stats.get('index_operations', 0)}")
            print(f"✅ Delete operations: {stats.get('delete_operations', 0)}")
            print(f"✅ Errors: {stats.get('errors', 0)}")
            
            test_results.append(("File Watcher Statistics", "PASSED"))
        
        except Exception as e:
            print(f"❌ File Watcher Statistics test failed: {e}")
            test_results.append(("File Watcher Statistics", "FAILED", str(e)))
            all_tests_passed = False
        
        # Final cleanup
        print("\n" + "=" * 60)
        print("CLEANUP")
        print("=" * 60)
        
        try:
            # Stop file watcher
            stop_result = await file_watcher_service.stop_watching()
            print(f"✅ File watcher stopped: {stop_result['status']}")
        except Exception as e:
            print(f"⚠️  Error stopping file watcher: {e}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("M2 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for result in test_results:
            test_name = result[0]
            status = result[1]
            
            if status == "PASSED":
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                error = result[2] if len(result) > 2 else "Unknown error"
                print(f"❌ {test_name}: FAILED - {error}")
                failed += 1
        
        print(f"\nTotal Tests: {len(test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed / len(test_results) * 100):.1f}%")
        
        if all_tests_passed:
            print("\n🎉 ALL M2 TESTS PASSED! File watcher and auto-indexing are working correctly.")
        else:
            print("\n❌ Some M2 tests failed. Check the logs above for details.")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ M2 testing failed with critical error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting M2 File Watcher and Auto-Indexing Tests")
    success = asyncio.run(test_m2_file_watcher_functionality())
    sys.exit(0 if success else 1) 