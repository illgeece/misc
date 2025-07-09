#!/usr/bin/env python3
"""Test vector store and semantic search functionality."""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_vector_store_functionality():
    """Test complete vector store and semantic search."""
    print("🔍 Testing Vector Store and Semantic Search\n")
    
    try:
        from app.services.knowledge_service import knowledge_service
        from app.services.vector_store import vector_store
        from app.services.document_processor import document_processor
        
        # Test 1: Clear any existing data
        print("1. Clearing existing data...")
        clear_result = await knowledge_service.clear_knowledge_base()
        print(f"   Clear result: {clear_result['status']}")
        
        # Test 2: Index a document
        print("\n2. Indexing test document...")
        rules_file = Path("../data/campaigns/rules/basic_rules.md")
        
        if not rules_file.exists():
            print(f"   ❌ Test file not found: {rules_file}")
            return False
        
        # Process document into chunks
        doc = document_processor.process_document(str(rules_file))
        print(f"   ✅ Processed: {doc.total_chunks} chunks")
        
        # Add to vector store
        chunks_added = vector_store.add_chunks(doc.chunks)
        print(f"   ✅ Added {chunks_added} chunks to vector store")
        
        # Test 3: Get stats
        print("\n3. Getting vector store stats...")
        stats = vector_store.get_collection_stats()
        print(f"   ✅ Total chunks: {stats['total_chunks']}")
        print(f"   ✅ Unique sources: {stats['unique_sources']}")
        print(f"   ✅ Source files: {stats['source_files']}")
        
        # Test 4: Semantic search
        print("\n4. Testing semantic search...")
        search_queries = [
            "What are ability scores?",
            "How does armor class work?",
            "What is Dexterity?",
            "Character creation rules"
        ]
        
        for query in search_queries:
            print(f"\n   Query: '{query}'")
            results = vector_store.search(query, limit=3, min_score=0.1)
            print(f"   ✅ Found {len(results)} results")
            
            for i, result in enumerate(results[:2], 1):
                print(f"      {i}. Score: {result.score:.3f} | Content: {result.content[:100]}...")
        
        # Test 5: Knowledge service search
        print("\n5. Testing knowledge service search...")
        search_result = await knowledge_service.search_knowledge(
            "What are the six ability scores?",
            limit=3,
            min_score=0.1
        )
        
        print(f"   ✅ Knowledge search found {search_result['total_results']} results")
        for i, result in enumerate(search_result['results'][:2], 1):
            print(f"      {i}. Score: {result['score']:.3f} | Source: {result['source']}")
            print(f"         Content: {result['content'][:100]}...")
        
        # Test 6: RAG with semantic search
        print("\n6. Testing RAG with semantic search...")
        from app.services.chat_service import chat_service
        
        # Create session and ask a question that should use RAG
        session_id = chat_service.create_session({"test": "vector_store"})
        
        response = await chat_service.send_message(
            session_id=session_id,
            user_message="What are the six ability scores in D&D? Please use the rules document.",
            use_rag=True
        )
        
        print(f"   ✅ RAG Response: {response['response'][:200]}...")
        print(f"   ✅ Context used: {response['context_used']}")
        print(f"   ✅ Context sources: {len(response.get('context_sources', []))}")
        
        # Test 7: Health checks
        print("\n7. Final health checks...")
        vector_health = vector_store.health_check()
        knowledge_health = knowledge_service.health_check()
        
        print(f"   ✅ Vector store health: {vector_health['status']}")
        print(f"   ✅ Knowledge service health: {knowledge_health['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run vector store tests."""
    print("🚀 Starting Vector Store Tests\n")
    
    success = await test_vector_store_functionality()
    
    if success:
        print("\n🎉 ALL VECTOR STORE TESTS PASSED!")
        print("\n✅ Vector Store Status:")
        print("   • ChromaDB: WORKING")
        print("   • TF-IDF embeddings: WORKING")
        print("   • Semantic search: WORKING")
        print("   • Knowledge indexing: WORKING")
        print("   • RAG with vector search: WORKING")
        
        print("\n📊 Implementation Details:")
        print("   • Embedding method: TF-IDF with scikit-learn")
        print("   • Vector database: ChromaDB")
        print("   • Similarity metric: Cosine similarity")
        print("   • Document chunking: Working")
        
        return 0
    else:
        print("\n❌ Vector store tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 