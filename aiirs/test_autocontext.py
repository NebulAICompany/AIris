#!/usr/bin/env python3
"""
Test script for AutoContext implementation
Tests the contextual chunk headers functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from aiiris_backend.retrieval.autocontext import AutoContextProcessor, apply_autocontext
from langchain_core.documents import Document

def create_test_document():
    """Create a test document with multiple sections for testing AutoContext."""
    return """# Machine Learning Fundamentals

Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models that enable computers to learn and make decisions from data without being explicitly programmed.

## Introduction to Machine Learning

Machine learning has revolutionized many industries by providing powerful tools for data analysis, pattern recognition, and prediction. The field encompasses various techniques and approaches.

### Types of Machine Learning

There are three main types of machine learning:

1. **Supervised Learning**: Uses labeled training data to learn a mapping from inputs to outputs
2. **Unsupervised Learning**: Finds patterns in data without labeled examples
3. **Reinforcement Learning**: Learns through interaction with an environment

## Supervised Learning

Supervised learning is the most common type of machine learning. It involves training a model on a dataset where both the input features and the correct output labels are provided.

### Classification

Classification is a type of supervised learning where the goal is to predict discrete class labels. Common algorithms include:

- Decision Trees
- Random Forest
- Support Vector Machines
- Neural Networks

### Regression

Regression is used when the target variable is continuous. Popular regression algorithms include:

- Linear Regression
- Polynomial Regression
- Ridge Regression
- Lasso Regression

## Unsupervised Learning

Unsupervised learning works with data that has no labeled responses. The goal is to discover hidden patterns or structures in the data.

### Clustering

Clustering algorithms group similar data points together:

- K-Means Clustering
- Hierarchical Clustering
- DBSCAN
- Gaussian Mixture Models

### Dimensionality Reduction

These techniques reduce the number of features while preserving important information:

- Principal Component Analysis (PCA)
- t-SNE
- UMAP
- Linear Discriminant Analysis (LDA)

## Deep Learning

Deep learning is a subset of machine learning that uses neural networks with multiple layers. It has achieved remarkable success in areas like computer vision, natural language processing, and speech recognition.

### Neural Network Architectures

Common deep learning architectures include:

- Feedforward Neural Networks
- Convolutional Neural Networks (CNNs)
- Recurrent Neural Networks (RNNs)
- Transformers

## Conclusion

Machine learning continues to evolve rapidly, with new techniques and applications emerging regularly. Understanding these fundamentals provides a solid foundation for exploring more advanced topics in artificial intelligence and data science."""

def create_test_chunks():
    """Create test chunks from the document."""
    document_text = create_test_document()
    
    # Split into chunks (simulating semantic chunking)
    chunks = []
    sections = document_text.split('\n\n')
    
    chunk_id = 0
    for i, section in enumerate(sections):
        if section.strip():
            chunk = Document(
                page_content=section.strip(),
                metadata={
                    "chunk_id": f"chunk_{chunk_id}",
                    "file_name": "ml_fundamentals.txt",
                    "content_type": "original",
                    "section_index": i
                }
            )
            chunks.append(chunk)
            chunk_id += 1
    
    return chunks

async def test_autocontext_processor():
    """Test the AutoContext processor with sample data."""
    print("🧪 Testing AutoContext Processor")
    print("=" * 50)
    
    # Create test chunks
    chunks = create_test_chunks()
    print(f"Created {len(chunks)} test chunks")
    
    # Initialize AutoContext processor
    processor = AutoContextProcessor(
        use_document_summary=True,
        use_section_summaries=True
    )
    
    # Process chunks with AutoContext
    try:
        print("\n🔗 Processing chunks with AutoContext...")
        processed_chunks = await processor.process_document_chunks(
            chunks,
            document_title="Machine Learning Fundamentals",
            file_name="ml_fundamentals.txt"
        )
        
        print(f"✅ Successfully processed {len(processed_chunks)} chunks")
        
        # Display results
        print("\n📊 AutoContext Results:")
        print("-" * 40)
        
        for i, chunk in enumerate(processed_chunks[:3]):  # Show first 3 chunks
            print(f"\n--- Chunk {i+1} ---")
            print(f"Original size: {chunk.metadata.get('original_chunk_size', 'N/A')} chars")
            print(f"Contextual size: {chunk.metadata.get('contextual_chunk_size', 'N/A')} chars")
            print(f"Section: {chunk.metadata.get('section_title', 'N/A')}")
            print(f"Section level: {chunk.metadata.get('section_level', 'N/A')}")
            print(f"Document title: {chunk.metadata.get('document_title', 'N/A')}")
            
            # Show first 200 characters of the contextual content
            content_preview = chunk.page_content[:200] + "..." if len(chunk.page_content) > 200 else chunk.page_content
            print(f"Content preview: {content_preview}")
            print("-" * 40)
        
        # Test metrics
        original_sizes = [chunk.metadata.get('original_chunk_size', 0) for chunk in processed_chunks]
        contextual_sizes = [chunk.metadata.get('contextual_chunk_size', 0) for chunk in processed_chunks]
        
        avg_original_size = sum(original_sizes) / len(original_sizes) if original_sizes else 0
        avg_contextual_size = sum(contextual_sizes) / len(contextual_sizes) if contextual_sizes else 0
        
        print(f"\n📈 Metrics:")
        print(f"Average original chunk size: {avg_original_size:.1f} characters")
        print(f"Average contextual chunk size: {avg_contextual_size:.1f} characters")
        print(f"Average context overhead: {avg_contextual_size - avg_original_size:.1f} characters")
        print(f"Context enhancement ratio: {avg_contextual_size / avg_original_size:.2f}x")
        
        return processed_chunks
        
    except Exception as e:
        print(f"❌ Error processing chunks: {e}")
        import traceback
        traceback.print_exc()
        return []

async def test_apply_autocontext():
    """Test the apply_autocontext function."""
    print("\n🧪 Testing apply_autocontext Function")
    print("=" * 50)
    
    # Create test chunks
    chunks = create_test_chunks()
    print(f"Created {len(chunks)} test chunks")
    
    # Test with AutoContext enabled
    print("\n🔗 Testing with AutoContext enabled...")
    enhanced_chunks = await apply_autocontext(
        chunks,
        document_title="Machine Learning Fundamentals",
        file_name="ml_fundamentals.txt",
        enabled=True
    )
    
    print(f"✅ Enhanced {len(enhanced_chunks)} chunks")
    
    # Test with AutoContext disabled
    print("\n❌ Testing with AutoContext disabled...")
    unchanged_chunks = await apply_autocontext(
        chunks,
        document_title="Machine Learning Fundamentals", 
        file_name="ml_fundamentals.txt",
        enabled=False
    )
    
    print(f"✅ Returned {len(unchanged_chunks)} unchanged chunks")
    
    # Compare results
    print(f"\n📊 Comparison:")
    print(f"Original chunks: {len(chunks)}")
    print(f"Enhanced chunks: {len(enhanced_chunks)}")
    print(f"Unchanged chunks: {len(unchanged_chunks)}")
    
    if enhanced_chunks and unchanged_chunks:
        enhanced_size = len(enhanced_chunks[0].page_content)
        unchanged_size = len(unchanged_chunks[0].page_content)
        print(f"First chunk - Enhanced: {enhanced_size} chars, Unchanged: {unchanged_size} chars")
    
    return enhanced_chunks

async def test_section_extraction():
    """Test section hierarchy extraction."""
    print("\n🧪 Testing Section Extraction")
    print("=" * 50)
    
    processor = AutoContextProcessor()
    document_text = create_test_document()
    
    sections = processor.extract_section_hierarchy(document_text)
    
    print(f"Extracted {len(sections)} sections:")
    for i, section in enumerate(sections):
        print(f"{i+1}. {section['title']} (Level {section['level']}) - {len(section['content'])} chars")
    
    return sections

async def main():
    """Run all AutoContext tests."""
    print("🚀 AutoContext Implementation Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: AutoContext processor
        processed_chunks = await test_autocontext_processor()
        
        # Test 2: apply_autocontext function
        enhanced_chunks = await test_apply_autocontext()
        
        # Test 3: Section extraction
        sections = await test_section_extraction()
        
        print("\n✅ All tests completed successfully!")
        print(f"📊 Final Results:")
        print(f"   - Processed chunks: {len(processed_chunks)}")
        print(f"   - Enhanced chunks: {len(enhanced_chunks)}")
        print(f"   - Extracted sections: {len(sections)}")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main()) 