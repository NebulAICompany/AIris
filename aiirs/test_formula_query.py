#!/usr/bin/env python3
"""
Test with formula-specific query to retrieve mathematical content
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiiris_backend.retrieval.retriever import load_vectorstore, retrieve_top_k
from aiiris_backend.retrieval.rse import retrieve_with_rse
import logging

logging.basicConfig(level=logging.WARNING)
VECTORSTORE_PATH = "aiiris_backend/vectorstore"

def test_formula_query():
    """Test with a mathematical formula query"""
    
    if not os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print("❌ Vectorstore not found.")
        return
    
    print("🔄 Loading vectorstore...")
    load_vectorstore(VECTORSTORE_PATH)
    
    # Try a formula-specific query
    query = "C = C– + cYD formülü"
    
    print("=" * 80)
    print(f"🔍 FORMULA QUERY: {query}")
    print("=" * 80)
    
    # Traditional retrieval
    print("\n📋 TRADITIONAL RETRIEVAL:")
    traditional = retrieve_top_k(query, k=3)
    
    for i, result in enumerate(traditional, 1):
        print(f"\n🔹 CHUNK {i} (Score: {result.get('score', 0):.4f})")
        print(f"Type: {result.get('metadata', {}).get('content_type', 'unknown')}")
        content = result.get('content', '').strip()
        print(f"Content: {content[:200]}{'...' if len(content) > 200 else ''}")
    
    # RSE retrieval
    print(f"\n🧠 RSE RETRIEVAL:")
    rse_chunks, rse_scores = retrieve_with_rse(query, k=10, preset="precision")
    
    for i, chunk in enumerate(rse_chunks, 1):
        print(f"\n🔸 SEGMENT {i} (Score: {chunk.get('score', 0):.4f})")
        print(f"Type: {chunk.get('metadata', {}).get('content_type', 'unknown')}")
        if chunk.get('metadata', {}).get('rse_segment'):
            start = chunk['metadata'].get('rse_segment_start', '?')
            end = chunk['metadata'].get('rse_segment_end', '?')
            print(f"RSE Segment: {start}-{end}")
        content = chunk.get('content', '').strip()
        print(f"Content: {content[:200]}{'...' if len(content) > 200 else ''}")
    
    print(f"\n📊 COMPARISON:")
    print(f"Traditional: {len(traditional)} chunks")
    print(f"RSE: {len(rse_chunks)} segments")

def main():
    print("🧮 TESTING FORMULA-SPECIFIC QUERY")
    test_formula_query()

if __name__ == "__main__":
    main() 