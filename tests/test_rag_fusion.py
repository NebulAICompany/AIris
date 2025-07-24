#!/usr/bin/env python3
"""
Test script for RAG Fusion implementation
"""

import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.retrieval.rag_fusion import (
    generate_fusion_queries,
    reciprocal_rank_fusion,
    retrieve_with_fusion,
)
from backend.retrieval.retriever import load_vectorstore
from backend.orchestrator.query_orchestrator import run_orchestration


async def test_query_generation():
    """Test the query generation functionality"""
    print("🔍 Testing Query Generation...")

    test_queries = [
        "What is climate change?",
        "Türkiye'nin ekonomik durumu nedir?",
        "How does AI work?",
        "Bitcoin fiyatı nasıl belirlenir?",
    ]

    for query in test_queries:
        print(f"\n📝 Original query: {query}")
        try:
            generated_queries = await generate_fusion_queries(query, num_queries=3)
            print(f"✅ Generated {len(generated_queries)} queries:")
            for i, gen_query in enumerate(generated_queries, 1):
                print(f"   {i}. {gen_query}")
        except Exception as e:
            print(f"❌ Error generating queries: {e}")


def test_reciprocal_rank_fusion():
    """Test the Reciprocal Rank Fusion algorithm"""
    print("\n🔄 Testing Reciprocal Rank Fusion...")

    # Mock search results for testing
    mock_results = {
        "climate change effects": [
            {
                "content": "Climate change causes global warming",
                "metadata": {"file_name": "doc1.pdf"},
                "score": 0.9,
            },
            {
                "content": "Rising sea levels due to climate change",
                "metadata": {"file_name": "doc2.pdf"},
                "score": 0.8,
            },
            {
                "content": "Economic impact of climate change",
                "metadata": {"file_name": "doc3.pdf"},
                "score": 0.7,
            },
        ],
        "global warming impacts": [
            {
                "content": "Economic impact of climate change",
                "metadata": {"file_name": "doc3.pdf"},
                "score": 0.85,
            },
            {
                "content": "Climate change causes global warming",
                "metadata": {"file_name": "doc1.pdf"},
                "score": 0.75,
            },
            {
                "content": "Environmental effects of warming",
                "metadata": {"file_name": "doc4.pdf"},
                "score": 0.65,
            },
        ],
        "environmental changes": [
            {
                "content": "Rising sea levels due to climate change",
                "metadata": {"file_name": "doc2.pdf"},
                "score": 0.8,
            },
            {
                "content": "Environmental effects of warming",
                "metadata": {"file_name": "doc4.pdf"},
                "score": 0.7,
            },
            {
                "content": "Biodiversity loss from climate change",
                "metadata": {"file_name": "doc5.pdf"},
                "score": 0.6,
            },
        ],
    }

    try:
        fused_results = reciprocal_rank_fusion(mock_results, k=60)
        print(f"✅ RRF completed with {len(fused_results)} results:")
        for i, result in enumerate(fused_results[:5], 1):
            print(
                f"   {i}. Score: {result['fusion_score']:.4f} - {result['content'][:50]}..."
            )
    except Exception as e:
        print(f"❌ Error in RRF: {e}")


async def test_full_rag_fusion():
    """Test the complete RAG Fusion pipeline"""
    print("\n🚀 Testing Full RAG Fusion Pipeline...")

    # Load vectorstore first
    vectorstore_path = "backend/vectorstore"
    if os.path.exists(f"{vectorstore_path}/index.faiss"):
        print("📦 Loading vectorstore...")
        try:
            load_vectorstore(vectorstore_path)
            print("✅ Vectorstore loaded successfully")
        except Exception as e:
            print(f"❌ Error loading vectorstore: {e}")
            return
    else:
        print("⚠️  Vectorstore not found, skipping full pipeline test")
        return

    test_query = "What is artificial intelligence?"
    print(f"📝 Testing query: {test_query}")

    try:
        fusion_docs, fusion_metadata = await retrieve_with_fusion(
            test_query, k=10, num_queries=3, top_n=5
        )

        print(f"✅ RAG Fusion completed:")
        print(f"   - Queries used: {len(fusion_metadata.get('queries_used', []))}")
        print(f"   - Fusion applied: {fusion_metadata.get('fusion_applied', False)}")
        print(f"   - Final documents: {len(fusion_docs)}")

        if fusion_docs:
            print("📄 Top results:")
            for i, doc in enumerate(fusion_docs[:3], 1):
                content_preview = (
                    doc["content"][:100] + "..."
                    if len(doc["content"]) > 100
                    else doc["content"]
                )
                fusion_score = doc.get("fusion_score", "N/A")
                print(f"   {i}. Score: {fusion_score} - {content_preview}")

    except Exception as e:
        print(f"❌ Error in full RAG Fusion: {e}")


async def test_orchestrator_integration():
    """Test RAG Fusion integration with query orchestrator"""
    print("\n🎯 Testing Orchestrator Integration...")

    # Test with RAG Fusion enabled
    test_query = "What is machine learning?"
    print(f"📝 Testing query with RAG Fusion: {test_query}")

    try:
        response = await run_orchestration(
            query=test_query,
            web_search_enabled=False,
            wolfram_enabled=False,
            rag_fusion_enabled=True,
            session_id=None,
            selected_files=None,
        )

        print(f"✅ Orchestrator response (first 200 chars): {response[:200]}...")

    except Exception as e:
        print(f"❌ Error in orchestrator integration: {e}")

    # Test with RAG Fusion disabled (standard retrieval)
    print(f"\n📝 Testing query without RAG Fusion: {test_query}")

    try:
        response = await run_orchestration(
            query=test_query,
            web_search_enabled=False,
            wolfram_enabled=False,
            rag_fusion_enabled=False,
            session_id=None,
            selected_files=None,
        )

        print(f"✅ Standard response (first 200 chars): {response[:200]}...")

    except Exception as e:
        print(f"❌ Error in standard retrieval: {e}")


async def main():
    """Run all tests"""
    print("🧪 RAG Fusion Implementation Test Suite")
    print("=" * 50)

    await test_query_generation()
    test_reciprocal_rank_fusion()
    await test_full_rag_fusion()
    await test_orchestrator_integration()

    print("\n✨ Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())
