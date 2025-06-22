#!/usr/bin/env python3
"""
Test script for RSE (Relevant Segment Extraction) integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiiris_backend.retrieval.retriever import load_vectorstore, retrieve_top_k
from aiiris_backend.retrieval.rse import retrieve_with_rse, apply_rse_single_query
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VECTORSTORE_PATH = "aiiris_backend/vectorstore"

def test_traditional_retrieval():
    """Test traditional retrieval without RSE"""
    print("\n" + "="*60)
    print("TESTING TRADITIONAL RETRIEVAL")
    print("="*60)
    
    # Load vectorstore
    if not os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print("❌ Vectorstore not found. Please run the upload pipeline first.")
        return []
    
    load_vectorstore(VECTORSTORE_PATH)
    
    # Test query
    query = "financial analysis budget"
    print(f"Query: {query}")
    
    # Traditional retrieval
    results = retrieve_top_k(query, k=10)
    print(f"Traditional retrieval returned {len(results)} results")
    
    # Show first few results
    for i, result in enumerate(results[:3]):
        print(f"\nResult {i+1}:")
        print(f"  Score: {result.get('score', 'N/A')}")
        print(f"  Metadata: {result.get('metadata', {})}")
        print(f"  Content: {result.get('content', '')[:100]}...")
    
    return results

def test_rse_retrieval():
    """Test RSE-enhanced retrieval"""
    print("\n" + "="*60)
    print("TESTING RSE-ENHANCED RETRIEVAL")
    print("="*60)
    
    # Load vectorstore
    if not os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print("❌ Vectorstore not found. Please run the upload pipeline first.")
        return [], []
    
    load_vectorstore(VECTORSTORE_PATH)
    
    # Test query
    query = "financial analysis budget"
    print(f"Query: {query}")
    
    # RSE-enhanced retrieval
    rse_chunks, rse_scores = retrieve_with_rse(query, k=15, preset="balanced")
    print(f"RSE retrieval returned {len(rse_chunks)} chunks with {len(rse_scores)} segment scores")
    
    # Show first few results
    for i, chunk in enumerate(rse_chunks[:3]):
        print(f"\nRSE Chunk {i+1}:")
        print(f"  Score: {chunk.get('score', 'N/A')}")
        print(f"  RSE Segment: {chunk.get('metadata', {}).get('rse_segment', 'N/A')}")
        if 'rse_segment_start' in chunk.get('metadata', {}):
            print(f"  Segment Range: {chunk['metadata']['rse_segment_start']}-{chunk['metadata']['rse_segment_end']}")
        print(f"  Metadata: {chunk.get('metadata', {})}")
        print(f"  Content: {chunk.get('content', '')[:100]}...")
    
    if rse_scores:
        print(f"\nSegment Scores: {rse_scores}")
    
    return rse_chunks, rse_scores

def test_rse_with_multiple_queries():
    """Test RSE with multiple related queries"""
    print("\n" + "="*60)
    print("TESTING RSE WITH MULTIPLE QUERIES")
    print("="*60)
    
    # Load vectorstore
    if not os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print("❌ Vectorstore not found. Please run the upload pipeline first.")
        return [], []
    
    load_vectorstore(VECTORSTORE_PATH)
    
    # Multiple related queries
    queries = [
        "financial analysis budget",
        "economic indicators market",
        "business performance metrics"
    ]
    
    print(f"Queries: {queries}")
    
    # Get results for each query
    all_results = []
    for query in queries:
        results = retrieve_top_k(query, k=10)
        all_results.append(results)
        print(f"Query '{query}' returned {len(results)} results")
    
    if not any(all_results):
        print("❌ No results found for any query")
        return [], []
    
    # Apply RSE to multiple queries
    from aiiris_backend.retrieval.rse import apply_rse
    rse_chunks, rse_scores = apply_rse(all_results, preset="balanced")
    
    print(f"\nRSE with multiple queries returned {len(rse_chunks)} chunks with {len(rse_scores)} segment scores")
    
    # Show first few results
    for i, chunk in enumerate(rse_chunks[:3]):
        print(f"\nMulti-Query RSE Chunk {i+1}:")
        print(f"  Score: {chunk.get('score', 'N/A')}")
        print(f"  RSE Segment: {chunk.get('metadata', {}).get('rse_segment', 'N/A')}")
        if 'rse_segment_start' in chunk.get('metadata', {}):
            print(f"  Segment Range: {chunk['metadata']['rse_segment_start']}-{chunk['metadata']['rse_segment_end']}")
        print(f"  Content: {chunk.get('content', '')[:100]}...")
    
    if rse_scores:
        print(f"\nSegment Scores: {rse_scores}")
    
    return rse_chunks, rse_scores

def test_analiz_document_prompts():
    """
    Test RSE with specific prompts based on analiz.docx content
    
    DOCUMENT CONTENT MAPPING:
    ========================
    analiz.docx contains a Turkish academic text about Keynesian consumption theory with these key sections:
    
    📍 SECTION 6.1: "KEYNESYEN TÜKETİM VE TASARRUF FONKSİYONLARI" 
       - Contains: C = C– + cYD formula, MPC definition, autonomous consumption explanation
       - Should be retrieved by: definition queries, formula queries, concept queries
    
    📍 Mathematical Formulas Section:
       - Contains: MPC = ∆C/∆YD, marjinal tüketim eğilimi calculations
       - Should be retrieved by: formula calculation queries
    
    📍 SECTION 6.2: "HANEHALKININ TÜKETİM KARARI: ZAMANLARARASI OPTİMİZASYON MODELİ"
       - Contains: Irving Fisher's intertemporal optimization model
       - Should be retrieved by: model-specific queries
    
    📍 Life-cycle Income Hypothesis Section:
       - Contains: F. Modigliani, A. Ando, R. Brumberg references and theory
       - Should be retrieved by: author/hypothesis queries
    
    📍 Empirical Evidence Section:
       - Contains: S. Kuznets findings from 1869-1940s about consumption-income stability
       - Should be retrieved by: empirical/historical queries
    
    📍 Interest Rate Effects Section:
       - Contains: faiz oranı effects on consumption decisions, budget constraints
       - Should be retrieved by: mechanism/effect queries
    """
    print("\n" + "="*60)
    print("TESTING ANALIZ.DOCX SPECIFIC PROMPTS")
    print("="*60)
    
    # Load vectorstore
    if not os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print("❌ Vectorstore not found. Please run the upload pipeline first.")
        return
    
    load_vectorstore(VECTORSTORE_PATH)
    
    # Specific test prompts based on analiz.docx content
    test_prompts = [
        {
            "query": "Keynesyen tüketim fonksiyonu nedir?",
            "expected_content": "C = C– + cYD formula and explanation of Keynesian consumption function",
            "target_section": "Section 6.1 - Keynesian Consumption and Savings Functions",
            "type": "definition_search"
        },
        {
            "query": "marjinal tüketim eğilimi nasıl hesaplanır?",
            "expected_content": "MPC = ∆C/∆YD formula and marginal propensity to consume explanation",
            "target_section": "Mathematical formulas and MPC definition",
            "type": "formula_search"
        },
        {
            "query": "otonom tüketim ne demektir?",
            "expected_content": "Definition of autonomous consumption (C–) independent of income level",
            "target_section": "Autonomous consumption explanation",
            "type": "concept_search"
        },
        {
            "query": "zamanlar arası optimizasyon modeli",
            "expected_content": "Irving Fisher's intertemporal optimization model explanation",
            "target_section": "Section 6.2 - Household Consumption Decision",
            "type": "model_search"
        },
        {
            "query": "yaşam boyu gelir hipotezi kimler tarafından geliştirilmiştir?",
            "expected_content": "F. Modigliani, A. Ando and R. Brumberg's life-cycle income hypothesis",
            "target_section": "Life-cycle income hypothesis section",
            "type": "author_search"
        },
        {
            "query": "faiz oranı tüketim kararını nasıl etkiler?",
            "expected_content": "Interest rate effects on consumption decisions and intertemporal choice",
            "target_section": "Intertemporal budget constraint and consumer preferences",
            "type": "mechanism_search"
        },
        {
            "query": "tüketim fonksiyonunun temel özellikleri nelerdir?",
            "expected_content": "Four main properties of consumption function listed as (1), (2), (3), (4)",
            "target_section": "Properties of linear consumption function",
            "type": "properties_search"
        },
        {
            "query": "Kuznets'in bulguları nelerdir?",
            "expected_content": "S. Kuznets findings about consumption-income ratio stability from 1869-1940s",
            "target_section": "Empirical evidence against Keynesian consumption function",
            "type": "empirical_search"
        }
    ]
    
    print(f"Testing {len(test_prompts)} specific prompts based on analiz.docx content:")
    print("="*60)
    
    successful_tests = 0
    total_rse_chunks = 0
    
    for i, prompt_test in enumerate(test_prompts, 1):
        print(f"\n🧪 TEST {i}: {prompt_test['type'].upper()}")
        print(f"Query: {prompt_test['query']}")
        print(f"Expected: {prompt_test['expected_content']}")
        print(f"Target Section: {prompt_test['target_section']}")
        
        # Test with RSE
        rse_chunks, rse_scores = retrieve_with_rse(prompt_test['query'], k=15, preset="precision")
        total_rse_chunks += len(rse_chunks)
        
        if rse_chunks:
            print(f"✅ RSE found {len(rse_chunks)} relevant segments")
            successful_tests += 1
            
            # Show top result
            top_chunk = rse_chunks[0]
            print(f"   Top Result Score: {top_chunk.get('score', 'N/A')}")
            if 'rse_segment_start' in top_chunk.get('metadata', {}):
                print(f"   RSE Segment: {top_chunk['metadata']['rse_segment_start']}-{top_chunk['metadata']['rse_segment_end']}")
            
            content_preview = top_chunk.get('content', '')[:200]
            print(f"   Content Preview: {content_preview}...")
            
            # Check if content seems relevant (basic keyword check)
            query_keywords = prompt_test['query'].lower().split()
            content_lower = top_chunk.get('content', '').lower()
            
            relevant_keywords = [kw for kw in query_keywords if len(kw) > 3 and kw in content_lower]
            if relevant_keywords:
                print(f"   ✅ Found relevant keywords: {relevant_keywords}")
            else:
                print(f"   ⚠️  No obvious keyword matches found")
        else:
            print(f"❌ No results found for this query")
        
        print("-" * 50)
    
    # Summary
    print(f"\n📊 ANALIZ.DOCX TEST SUMMARY:")
    print(f"   Total tests: {len(test_prompts)}")
    print(f"   Successful retrievals: {successful_tests}")
    print(f"   Success rate: {(successful_tests/len(test_prompts)*100):.1f}%")
    print(f"   Average chunks per query: {total_rse_chunks/len(test_prompts):.1f}")
    
    if successful_tests >= len(test_prompts) * 0.7:  # 70% success rate
        print("✅ RSE integration with analiz.docx content: PASSED")
    else:
        print("⚠️  RSE integration with analiz.docx content: NEEDS IMPROVEMENT")
    
    return successful_tests, len(test_prompts)

def compare_retrieval_methods():
    """Compare traditional vs RSE retrieval"""
    print("\n" + "="*60)
    print("COMPARING RETRIEVAL METHODS")
    print("="*60)
    
    # Run both methods
    traditional_results = test_traditional_retrieval()
    rse_chunks, rse_scores = test_rse_retrieval()
    
    print(f"\nComparison:")
    print(f"  Traditional: {len(traditional_results)} results")
    print(f"  RSE: {len(rse_chunks)} optimized chunks")
    
    if traditional_results and rse_chunks:
        print(f"  Reduction: {len(traditional_results) - len(rse_chunks)} fewer chunks")
        print(f"  Efficiency: {len(rse_chunks)/len(traditional_results)*100:.1f}% of original")

def main():
    """Run all tests"""
    print("🧠 RSE (Relevant Segment Extraction) Integration Test")
    print("="*60)
    
    try:
        # Test traditional retrieval
        test_traditional_retrieval()
        
        # Test RSE-enhanced retrieval
        test_rse_retrieval()
        
        # Test RSE with multiple queries
        test_rse_with_multiple_queries()
        
        # Test analiz.docx specific prompts
        print("\n🎯 TESTING DOCUMENT-SPECIFIC PROMPTS")
        success_count, total_count = test_analiz_document_prompts()
        
        # Compare methods
        compare_retrieval_methods()
        
        print(f"\n🎉 RSE INTEGRATION TEST RESULTS:")
        print(f"   Document-specific tests: {success_count}/{total_count} successful")
        print("✅ All RSE tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 