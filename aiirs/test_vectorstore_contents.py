#!/usr/bin/env python3
"""
Vectorstore Contents Test Script
Tests and analyzes the contents of the AIris vectorstore to see which files are stored.
"""

import sys
import os
from pathlib import Path
from collections import defaultdict, Counter
import json
from datetime import datetime

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import our logging system
from aiiris_backend.libs.logger import setup_logging, get_logger

def get_embeddings():
    """Get embeddings with fallback options"""
    try:
        from langchain_openai import OpenAIEmbeddings
        logger.info("Trying OpenAI embeddings...")
        return OpenAIEmbeddings(model="text-embedding-3-small")
    except Exception as e:
        logger.warning(f"OpenAI embeddings failed: {e}")
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.info("Falling back to HuggingFace embeddings...")
            return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        except Exception as e2:
            logger.error(f"HuggingFace embeddings also failed: {e2}")
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                logger.info("Trying community HuggingFace embeddings...")
                return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            except Exception as e3:
                logger.error(f"All embedding options failed: {e3}")
                raise ImportError("No suitable embeddings found") from e3

def load_vectorstore():
    """Load and return the vectorstore if it exists"""
    try:
        from langchain_community.vectorstores import FAISS
        
        vectorstore_dir = Path('aiiris_backend/vectorstore')
        
        if not vectorstore_dir.exists():
            logger.error(f"Vectorstore directory not found: {vectorstore_dir}")
            return None
            
        if not (vectorstore_dir / "index.faiss").exists():
            logger.error(f"FAISS index file not found in: {vectorstore_dir}")
            return None
            
        logger.info(f"Loading vectorstore from: {vectorstore_dir}")
        embeddings = get_embeddings()
        vectorstore = FAISS.load_local(
            str(vectorstore_dir), 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        
        logger.info("Vectorstore loaded successfully")
        return vectorstore
        
    except ImportError as e:
        logger.error(f"Failed to import required libraries: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load vectorstore: {e}")
        return None

def analyze_vectorstore_contents(vectorstore):
    """Analyze and report on vectorstore contents"""
    if not vectorstore:
        logger.error("No vectorstore provided for analysis")
        return
    
    logger.info("Starting vectorstore content analysis...")
    
    # Basic statistics
    total_docs = len(vectorstore.docstore._dict)
    logger.info(f"Total documents in vectorstore: {total_docs}")
    
    if total_docs == 0:
        logger.warning("Vectorstore is empty!")
        return
    
    # Analyze documents by file
    file_stats = defaultdict(lambda: {'chunks': 0, 'total_chars': 0, 'doc_ids': []})
    metadata_fields = set()
    chunk_sizes = []
    
    logger.info("Analyzing document metadata and content...")
    
    for doc_id, document in vectorstore.docstore._dict.items():
        # Collect metadata fields
        metadata_fields.update(document.metadata.keys())
        
        # Get filename
        filename = document.metadata.get('file_name', 'Unknown')
        
        # Update file statistics
        file_stats[filename]['chunks'] += 1
        file_stats[filename]['total_chars'] += len(document.page_content)
        file_stats[filename]['doc_ids'].append(doc_id)
        
        # Track chunk sizes
        chunk_sizes.append(len(document.page_content))
    
    # Report file statistics
    logger.info("\n" + "="*60)
    logger.info("FILE ANALYSIS RESULTS")
    logger.info("="*60)
    
    if 'Unknown' in file_stats and len(file_stats) == 1:
        logger.warning("All documents have unknown filenames - metadata may be missing!")
    
    for filename, stats in sorted(file_stats.items()):
        logger.info(f"\nFile: {filename}")
        logger.info(f"  Chunks: {stats['chunks']}")
        logger.info(f"  Total characters: {stats['total_chars']:,}")
        logger.info(f"  Average chunk size: {stats['total_chars'] // stats['chunks']:,} chars")
        logger.info(f"  Doc IDs: {stats['doc_ids'][:5]}{'...' if len(stats['doc_ids']) > 5 else ''}")
    
    # Metadata analysis
    logger.info(f"\nMetadata fields found: {sorted(metadata_fields)}")
    
    # Chunk size statistics
    if chunk_sizes:
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        min_chunk_size = min(chunk_sizes)
        max_chunk_size = max(chunk_sizes)
        
        logger.info(f"\nChunk size statistics:")
        logger.info(f"  Average: {avg_chunk_size:.0f} characters")
        logger.info(f"  Minimum: {min_chunk_size} characters")
        logger.info(f"  Maximum: {max_chunk_size} characters")
    
    return file_stats

def show_sample_documents(vectorstore, num_samples=3):
    """Show sample documents from the vectorstore"""
    logger.info(f"\nShowing {num_samples} sample documents:")
    logger.info("-" * 50)
    
    count = 0
    for doc_id, document in vectorstore.docstore._dict.items():
        if count >= num_samples:
            break
            
        logger.info(f"\nSample {count + 1}:")
        logger.info(f"  Doc ID: {doc_id}")
        logger.info(f"  Metadata: {document.metadata}")
        
        # Show content preview
        content_preview = document.page_content[:200]
        if len(document.page_content) > 200:
            content_preview += "..."
        logger.info(f"  Content preview: {repr(content_preview)}")
        logger.info(f"  Full content length: {len(document.page_content)} characters")
        
        count += 1

def check_pii_mappings():
    """Check the PII chunk mappings file"""
    pii_file = Path('aiiris_backend/vectorstore/pii_chunk_maps.json')
    
    if not pii_file.exists():
        logger.warning("PII chunk mappings file not found")
        return
    
    try:
        with open(pii_file, 'r') as f:
            pii_data = json.load(f)
        
        logger.info(f"\nPII Mappings Analysis:")
        logger.info(f"  Total PII chunk entries: {len(pii_data)}")
        
        # Count non-empty PII mappings
        non_empty_count = sum(1 for v in pii_data.values() if v)
        logger.info(f"  Non-empty PII mappings: {non_empty_count}")
        
        if non_empty_count > 0:
            logger.info("  Sample PII mappings:")
            sample_count = 0
            for chunk_id, pii_info in pii_data.items():
                if pii_info and sample_count < 3:
                    logger.info(f"    {chunk_id}: {pii_info}")
                    sample_count += 1
        
    except Exception as e:
        logger.error(f"Failed to read PII mappings: {e}")

def search_test(vectorstore, query="financial", k=3):
    """Test vectorstore search functionality"""
    logger.info(f"\nTesting search functionality with query: '{query}'")
    
    try:
        results = vectorstore.similarity_search(query, k=k)
        logger.info(f"Found {len(results)} results:")
        
        for i, doc in enumerate(results, 1):
            logger.info(f"\nResult {i}:")
            logger.info(f"  Metadata: {doc.metadata}")
            content_preview = doc.page_content[:150]
            if len(doc.page_content) > 150:
                content_preview += "..."
            logger.info(f"  Content: {repr(content_preview)}")
            
    except Exception as e:
        logger.error(f"Search test failed: {e}")

def main():
    """Main test function"""
    # Initialize logging
    setup_logging()
    global logger
    logger = get_logger(__name__)
    
    logger.info("Starting vectorstore contents test")
    logger.info("="*60)
    
    # Load vectorstore
    vectorstore = load_vectorstore()
    if not vectorstore:
        logger.error("Cannot continue without vectorstore")
        return
    
    # Analyze contents
    file_stats = analyze_vectorstore_contents(vectorstore)
    
    # Show samples
    show_sample_documents(vectorstore)
    
    # Check PII mappings
    check_pii_mappings()
    
    # Test search
    if file_stats:
        search_test(vectorstore)
    
    logger.info("\n" + "="*60)
    logger.info("Vectorstore contents test completed")
    logger.info("="*60)

if __name__ == "__main__":
    main() 