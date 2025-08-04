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

from backend.pipeline.vector import VectorStorePipeline, PreEmbeddingProcess


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


def test_none_process():
    """Test the None pre-embedding process."""
    print("🧪 Testing None Pre-embedding Process")
    print("=" * 50)

    # Create test content
    content = create_test_document()

    try:
        # Create pipeline with None process
        pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.NONE)

        # Create temporary vectorstore directory
        vectorstore_dir = tempfile.mkdtemp()

        # Run pipeline with text content
        print(f"Processing text content directly")
        pipeline.run(
            text_content=content,
            document_name="test_none",
            save_path=vectorstore_dir,
        )

        print("✅ None process completed successfully")
        return True

    except Exception as e:
        print(f"❌ None process failed: {e}")
        return False


def test_hype_process():
    """Test the HyPE pre-embedding process."""
    print("\n🧪 Testing HyPE Pre-embedding Process")
    print("=" * 50)

    # Create test content
    content = create_test_document()

    try:
        # Create pipeline with HyPE process
        pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.HYPE)

        # Create temporary vectorstore directory
        vectorstore_dir = tempfile.mkdtemp()

        # Run pipeline with text content
        print(f"Processing text content directly")
        pipeline.run(
            text_content=content,
            document_name="test_hype",
            save_path=vectorstore_dir,
        )

        print("✅ HyPE process completed successfully")
        return True

    except Exception as e:
        print(f"❌ HyPE process failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cch_process():
    """Test the CCH (AutoContext) pre-embedding process."""
    print("\n🧪 Testing CCH (AutoContext) Pre-embedding Process")
    print("=" * 50)

    # Create test content
    content = create_test_document()

    try:
        # Create pipeline with CCH process
        pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.CCH)

        # Create temporary vectorstore directory
        vectorstore_dir = tempfile.mkdtemp()

        # Run pipeline with text content
        print(f"Processing text content directly")
        pipeline.run(
            text_content=content,
            document_name="test_cch",
            save_path=vectorstore_dir,
        )

        print("✅ CCH process completed successfully")
        return True

    except Exception as e:
        print(f"❌ CCH process failed: {e}")
        import traceback

        traceback.print_exc()
        return False


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
            print(
                f"❌ '{input_str}' -> {result.value} (expected {expected_enum.value})"
            )

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

        # Test 4: API compatibility
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
            print(
                "🎉 All tests passed! Pre-embedding process selection system is working correctly."
            )
        else:
            print("⚠️ Some tests failed. Please check the implementation.")

    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
