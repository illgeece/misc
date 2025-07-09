#!/usr/bin/env python3
"""Basic test script for M1 functionality - Ollama integration and document processing."""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_ollama_connection():
    """Test basic Ollama connection and model availability."""
    print("🔍 Testing Ollama connection...")
    
    try:
        import ollama
        
        # Test connection
        client = ollama.Client(host="http://localhost:11434")
        
        # Check if model is available
        models = client.list()
        # Handle different response formats
        if hasattr(models, 'models'):
            model_list = models.models
        else:
            model_list = models.get('models', [])
        
        model_names = []
        for model in model_list:
            if hasattr(model, 'model'):
                model_names.append(model.model)
            elif hasattr(model, 'name'):
                model_names.append(model.name)
            elif isinstance(model, dict) and 'name' in model:
                model_names.append(model['name'])
            elif isinstance(model, dict) and 'model' in model:
                model_names.append(model['model'])
        
        # Debug: show what we got
        print(f"Extracted model names: {model_names}")
        
        print(f"✅ Available models: {model_names}")
        
        if 'gemma3:latest' in model_names:
            print("✅ Gemma 4B model is available")
            
            # Test simple generation
            response = client.chat(
                model='gemma3:latest',
                messages=[{"role": "user", "content": "Hello! Can you help with D&D?"}],
                options={'num_predict': 50}
            )
            
            print(f"✅ Test response: {response['message']['content'][:100]}...")
            return True
        else:
            print("❌ Gemma 4B model not found")
            return False
            
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False

async def test_document_processing():
    """Test document processing functionality."""
    print("\n🔍 Testing document processing...")
    
    try:
        from app.services.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        
        # Test with the basic rules markdown file
        rules_file = Path("../data/campaigns/rules/basic_rules.md")
        
        if rules_file.exists():
            print(f"✅ Found test file: {rules_file}")
            
            # Process the document
            processed_doc = processor.process_document(str(rules_file))
            
            print(f"✅ Processed document: {processed_doc.total_chunks} chunks")
            print(f"✅ Processing time: {processed_doc.processing_time_ms}ms")
            print(f"✅ First chunk preview: {processed_doc.chunks[0].content[:100]}...")
            
            return True
        else:
            print(f"❌ Test file not found: {rules_file}")
            return False
            
    except Exception as e:
        print(f"❌ Document processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_llm_service():
    """Test LLM service functionality."""
    print("\n🔍 Testing LLM service...")
    
    try:
        from app.services.llm_service import LLMService, ChatMessage
        
        llm = LLMService()
        
        # Test basic generation
        messages = [ChatMessage(role="user", content="What is armor class in D&D?")]
        
        response = await llm.generate_response(messages)
        
        print(f"✅ LLM response: {response.content[:150]}...")
        print(f"✅ Model: {response.model}")
        print(f"✅ Response time: {response.response_time_ms}ms")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM service failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_basic_rag():
    """Test basic RAG without vector store."""
    print("\n🔍 Testing basic RAG (without vector store)...")
    
    try:
        from app.services.document_processor import DocumentProcessor
        from app.services.llm_service import LLMService, ChatMessage
        
        processor = DocumentProcessor()
        llm = LLMService()
        
        # Process rules document
        rules_file = Path("../data/campaigns/rules/basic_rules.md")
        
        if not rules_file.exists():
            print(f"❌ Test file not found: {rules_file}")
            return False
        
        processed_doc = processor.process_document(str(rules_file))
        
        # Create simple context from first few chunks
        context_chunks = processed_doc.chunks[:3]
        context = "\n\n---\n\n".join([chunk.content for chunk in context_chunks])
        
        # Test RAG-style query
        user_question = "What are ability scores?"
        messages = [ChatMessage(role="user", content=user_question)]
        
        response = await llm.generate_response(
            messages=messages,
            system_prompt="You are a D&D assistant. Answer based on the provided context.",
            context=f"Context from rules:\n{context}"
        )
        
        print(f"✅ RAG response: {response.content[:200]}...")
        print(f"✅ Context length: {len(context)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_imports():
    """Test that API endpoints can be imported."""
    print("\n🔍 Testing API imports...")
    
    try:
        # Test importing the services and endpoints
        from app.services.llm_service import llm_service
        from app.services.document_processor import document_processor
        from app.api.endpoints.chat import router as chat_router
        
        print("✅ Successfully imported llm_service")
        print("✅ Successfully imported document_processor")
        print("✅ Successfully imported chat router")
        
        # Test basic health checks
        llm_health = llm_service.health_check()
        print(f"✅ LLM service health: {llm_health.get('status', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting M1 Basic Tests\n")
    
    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("Document Processing", test_document_processing),
        ("LLM Service", test_llm_service),
        ("Basic RAG", test_basic_rag),
        ("API Imports", test_api_imports),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! M1 basic functionality is working.")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 