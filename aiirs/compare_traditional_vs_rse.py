#!/usr/bin/env python3
"""
Direct comparison: Traditional vs RSE retrieval for a single query
Shows actual content differences side-by-side
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiiris_backend.retrieval.retriever import load_vectorstore, retrieve_top_k
from aiiris_backend.retrieval.rse import retrieve_with_rse
import logging

# Setup logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

VECTORSTORE_PATH = "aiiris_backend/vectorstore"

def compare_single_query():
    """Compare traditional vs RSE for a single query with detailed content display"""
    
    # Load vectorstore
    if not os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print("❌ Vectorstore not found. Please run the upload pipeline first.")
        return
    
    print("🔄 Loading vectorstore...")
    load_vectorstore(VECTORSTORE_PATH)
    
    # Single test query based on analiz.docx content
    test_query = "Keynesyen tüketim fonksiyonu nedir?"
    
    print("=" * 80)
    print(f"🔍 QUERY: {test_query}")
    print("=" * 80)
    
    # 1. TRADITIONAL RETRIEVAL
    print("\n📋 TRADITIONAL RETRIEVAL (Top-K Chunks)")
    print("-" * 50)
    
    traditional_results = retrieve_top_k(test_query, k=5)
    
    if traditional_results:
        for i, result in enumerate(traditional_results, 1):
            print(f"\n🔹 CHUNK {i} (Score: {result.get('score', 'N/A'):.4f})")
            print(f"📁 File: {result.get('metadata', {}).get('file_name', 'Unknown')}")
            print(f"🏷️  Chunk ID: {result.get('metadata', {}).get('chunk_id', 'Unknown')}")
            print(f"📄 Content Type: {result.get('metadata', {}).get('content_type', 'Unknown')}")
            print("📝 Content:")
            content = result.get('content', '').strip()
            print(f"   {content}{'...' if len(content) > 0 else ''}")
            print("-" * 30)
    else:
        print("❌ No traditional results found")
    
    # 2. RSE RETRIEVAL
    print(f"\n🧠 RSE RETRIEVAL (Optimized Segments)")
    print("-" * 50)
    
    rse_chunks, rse_scores = retrieve_with_rse(test_query, k=15, preset="precision")
    
    if rse_chunks:
        print(f"🎯 RSE found {len(rse_chunks)} optimized segments from {len(traditional_results)} initial chunks")
        
        for i, chunk in enumerate(rse_chunks, 1):
            print(f"\n🔸 SEGMENT {i} (Score: {chunk.get('score', 'N/A'):.4f})")
            print(f"📁 File: {chunk.get('metadata', {}).get('file_name', 'Unknown')}")
            print(f"🏷️  Chunk ID: {chunk.get('metadata', {}).get('chunk_id', 'Unknown')}")
            print(f"📄 Content Type: {chunk.get('metadata', {}).get('content_type', 'Unknown')}")
            
            # RSE-specific metadata
            if chunk.get('metadata', {}).get('rse_segment'):
                start = chunk['metadata'].get('rse_segment_start', 'N/A')
                end = chunk['metadata'].get('rse_segment_end', 'N/A')
                print(f"🎯 RSE Segment Range: {start}-{end}")
            
            print("📝 Content:")
            content = chunk.get('content', '').strip()
            print(f"   {content}{'...' if len(content) > 0 else ''}")
            print("-" * 30)
    else:
        print("❌ No RSE results found")
    
    # 3. COMPARISON SUMMARY
    print(f"\n📊 COMPARISON SUMMARY")
    print("=" * 50)
    print(f"Traditional Chunks: {len(traditional_results)}")
    print(f"RSE Segments: {len(rse_chunks)}")
    
    if traditional_results and rse_chunks:
        reduction = len(traditional_results) - len(rse_chunks)
        efficiency = (len(rse_chunks) / len(traditional_results)) * 100
        print(f"Reduction: {reduction} fewer pieces")
        print(f"Efficiency: {efficiency:.1f}% of original")
        
        # Check for content overlap
        trad_content = set([r.get('content', '')[:100] for r in traditional_results])
        rse_content = set([r.get('content', '')[:100] for r in rse_chunks])
        overlap = len(trad_content.intersection(rse_content))
        
        print(f"Content Overlap: {overlap}/{len(traditional_results)} chunks")
        
        if len(rse_chunks) < len(traditional_results):
            print("✅ RSE successfully reduced chunks while maintaining relevance")
        elif len(rse_chunks) == len(traditional_results):
            print("🔄 RSE kept same number but may have reordered by relevance")
        else:
            print("📈 RSE expanded to include more relevant segments")
    
    # 4. CONTENT ANALYSIS
    print(f"\n🔍 CONTENT RELEVANCE ANALYSIS")
    print("=" * 50)
    
    query_keywords = ["keynesyen", "tüketim", "fonksiyon", "consumption", "keynesian"]
    
    print("🔹 Traditional Results:")
    for i, result in enumerate(traditional_results, 1):
        content_lower = result.get('content', '').lower()
        found_keywords = [kw for kw in query_keywords if kw in content_lower]
        print(f"   Chunk {i}: {len(found_keywords)} keywords → {found_keywords}")
    
    print("\n🔸 RSE Results:")
    for i, chunk in enumerate(rse_chunks, 1):
        content_lower = chunk.get('content', '').lower()
        found_keywords = [kw for kw in query_keywords if kw in content_lower]
        print(f"   Segment {i}: {len(found_keywords)} keywords → {found_keywords}")

def main():
    """Run the focused comparison"""
    print("🎯 Traditional vs RSE - Single Query Comparison")
    print("=" * 80)
    
    try:
        compare_single_query()
        print("\n✅ Comparison completed!")
        
    except Exception as e:
        print(f"\n❌ Error during comparison: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 