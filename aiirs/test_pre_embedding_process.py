#!/usr/bin/env python3
"""
Test script for Pre-embedding Process Selection System
Tests the None, HyPE, and CCH (AutoContext) options
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from aiiris_backend.pipelines.vectorpipe import VectorStorePipeline, PreEmbeddingProcess
from langchain_core.documents import Document

def create_test_document():
    """Create a test document for processing."""
    return """# Financial Report Analysis

This document provides an analysis of quarterly financial performance.

## Executive Summary

The company achieved strong financial results in Q3 2024, with revenue growth of 15% year-over-year.

### Key Metrics

- Revenue: $2.5 million
- Net Income: $450,000
- Operating Margin: 18%

## Detailed Analysis

### Revenue Performance

Revenue increased significantly due to new product launches and market expansion.

### Cost Management

Operating expenses were well-controlled, leading to improved profitability.

## Conclusion

The financial outlook remains positive for the upcoming quarter.
"""

def create_test_file(content: str, filename: str) -> str:
    """Create a temporary test file."""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path

def test_none_process():
    """Test the None pre-embedding process."""
    print("🧪 Testing None Pre-embedding Process")
    print("=" * 50)
    
    # Create test file
    content = create_test_document()
    temp_file = create_test_file(content, "test_none.txt")
    temp_dir = os.path.dirname(temp_file)
    
    try:
        # Create pipeline with None process
        pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.NONE)
        
        # Create temporary vectorstore directory
        vectorstore_dir = tempfile.mkdtemp()
        
        # Run pipeline
        print(f"Processing file: {temp_file}")
        pipeline.run(
            uploads_path=temp_dir,
            save_path=vectorstore_dir,
            specific_file="test_none.txt"
        )
        
        print("✅ None process completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ None process failed: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)

def test_hype_process():
    """Test the HyPE pre-embedding process."""
    print("\n🧪 Testing HyPE Pre-embedding Process")
    print("=" * 50)
    
    # Create test file
    content = create_test_document()
    temp_file = create_test_file(content, "test_hype.txt")
    temp_dir = os.path.dirname(temp_file)
    
    try:
        # Create pipeline with HyPE process
        pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.HYPE)
        
        # Create temporary vectorstore directory
        vectorstore_dir = tempfile.mkdtemp()
        
        # Run pipeline
        print(f"Processing file: {temp_file}")
        pipeline.run(
            uploads_path=temp_dir,
            save_path=vectorstore_dir,
            specific_file="test_hype.txt"
        )
        
        print("✅ HyPE process completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ HyPE process failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)

def test_cch_process():
    """Test the CCH (AutoContext) pre-embedding process."""
    print("\n🧪 Testing CCH (AutoContext) Pre-embedding Process")
    print("=" * 50)
    
    # Create test file
    content = create_test_document()
    temp_file = create_test_file(content, "test_cch.txt")
    temp_dir = os.path.dirname(temp_file)
    
    try:
        # Create pipeline with CCH process
        pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.CCH)
        
        # Create temporary vectorstore directory
        vectorstore_dir = tempfile.mkdtemp()
        
        # Run pipeline
        print(f"Processing file: {temp_file}")
        pipeline.run(
            uploads_path=temp_dir,
            save_path=vectorstore_dir,
            specific_file="test_cch.txt"
        )
        
        print("✅ CCH process completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ CCH process failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)

def test_legacy_hype_pipeline():
    """Test the legacy HyPEVectorStorePipeline for backward compatibility."""
    print("\n🧪 Testing Legacy HyPEVectorStorePipeline")
    print("=" * 50)
    
    from aiiris_backend.pipelines.vectorpipe import HyPEVectorStorePipeline
    
    # Create test file
    content = create_test_document()
    temp_file = create_test_file(content, "test_legacy.txt")
    temp_dir = os.path.dirname(temp_file)
    
    try:
        # Create legacy pipeline
        pipeline = HyPEVectorStorePipeline(autocontext_enabled=False)
        
        # Create temporary vectorstore directory
        vectorstore_dir = tempfile.mkdtemp()
        
        # Run pipeline
        print(f"Processing file: {temp_file}")
        pipeline.run(
            uploads_path=temp_dir,
            save_path=vectorstore_dir,
            specific_file="test_legacy.txt"
        )
        
        print("✅ Legacy HyPE pipeline completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Legacy HyPE pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)

def test_api_compatibility():
    """Test API parameter compatibility."""
    print("\n🧪 Testing API Parameter Compatibility")
    print("=" * 50)
    
    # Test parameter conversion
    test_cases = [
        ("none", PreEmbeddingProcess.NONE),
        ("hype", PreEmbeddingProcess.HYPE),
        ("cch", PreEmbeddingProcess.CCH),
        ("NONE", PreEmbeddingProcess.NONE),
        ("HYPE", PreEmbeddingProcess.HYPE),
        ("CCH", PreEmbeddingProcess.CCH),
    ]
    
    for input_str, expected_enum in test_cases:
        # Convert string to enum (simulating API conversion)
        if input_str.lower() == "hype":
            result = PreEmbeddingProcess.HYPE
        elif input_str.lower() == "cch":
            result = PreEmbeddingProcess.CCH
        else:
            result = PreEmbeddingProcess.NONE
        
        if result == expected_enum:
            print(f"✅ '{input_str}' -> {result.value}")
        else:
            print(f"❌ '{input_str}' -> {result.value} (expected {expected_enum.value})")
    
    return True

def main():
    """Run all pre-embedding process tests."""
    print("🚀 Pre-embedding Process Selection Test Suite")
    print("=" * 60)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not set. HyPE and CCH tests may fail.")
    
    results = []
    
    try:
        # Test 1: None process
        results.append(("None Process", test_none_process()))
        
        # Test 2: HyPE process
        results.append(("HyPE Process", test_hype_process()))
        
        # Test 3: CCH process
        results.append(("CCH Process", test_cch_process()))
        
        # Test 4: Legacy compatibility
        results.append(("Legacy HyPE", test_legacy_hype_pipeline()))
        
        # Test 5: API compatibility
        results.append(("API Compatibility", test_api_compatibility()))
        
        # Summary
        print("\n📊 Test Results Summary:")
        print("=" * 40)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Pre-embedding process selection system is working correctly.")
        else:
            print("⚠️ Some tests failed. Please check the implementation.")
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 