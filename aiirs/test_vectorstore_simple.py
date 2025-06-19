#!/usr/bin/env python3
"""
Simple Vectorstore Contents Test Script
Reads the vectorstore pickle file directly to see which files are stored.
"""

import sys
import pickle
from pathlib import Path
from collections import defaultdict
import json

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import our logging system
from aiiris_backend.libs.logger import setup_logging, get_logger

def read_vectorstore_pickle():
    """Read the vectorstore pickle file directly"""
    pickle_file = Path('aiiris_backend/vectorstore/index.pkl')
    
    if not pickle_file.exists():
        logger.error(f"Pickle file not found: {pickle_file}")
        return None
    
    try:
        logger.info(f"Reading pickle file: {pickle_file}")
        with open(pickle_file, 'rb') as f:
            data = pickle.load(f)
        
        logger.info("Pickle file loaded successfully")
        return data
    except Exception as e:
        logger.error(f"Failed to read pickle file: {e}")
        return None

def analyze_pickle_data(data):
    """Analyze the data from the pickle file"""
    if not data:
        logger.error("No data to analyze")
        return
    
    logger.info("Analyzing pickle data structure...")
    logger.info(f"Type: {type(data)}")
    
    # Handle tuple structure (common in FAISS saved data)
    if isinstance(data, tuple):
        logger.info(f"Tuple with {len(data)} elements:")
        for i, item in enumerate(data):
            logger.info(f"  Element {i}: {type(item)}")
            
            # Check if this element is a docstore directly
            if 'docstore' in str(type(item)).lower() or hasattr(item, '_dict'):
                logger.info(f"  Found docstore-like object in element {i}")
                analyze_docstore(item)
                return
            
            # Check if this element has docstore
            elif hasattr(item, 'docstore'):
                logger.info(f"  Found docstore in element {i}")
                analyze_docstore(item.docstore)
                return
    
    # Handle direct object
    elif hasattr(data, 'docstore'):
        logger.info("Found docstore in main object")
        analyze_docstore(data.docstore)
        return
    
    # Generic object analysis
    if hasattr(data, '__dict__'):
        logger.info("Object attributes:")
        for attr in dir(data):
            if not attr.startswith('_'):
                try:
                    attr_value = getattr(data, attr, None)
                    logger.info(f"  {attr}: {type(attr_value)}")
                    # Check if this attribute has docstore
                    if hasattr(attr_value, 'docstore'):
                        logger.info(f"  Found docstore in {attr}")
                        analyze_docstore(attr_value.docstore)
                        return
                except:
                    logger.info(f"  {attr}: <could not access>")
    
    logger.warning("Could not find docstore structure in the data")

def analyze_docstore(docstore):
    """Analyze the docstore structure"""
    logger.info(f"Docstore type: {type(docstore)}")
    
    if hasattr(docstore, '_dict'):
        docs_dict = docstore._dict
        logger.info(f"Total documents in docstore: {len(docs_dict)}")
        analyze_documents(docs_dict)
    elif hasattr(docstore, 'docs'):
        docs = docstore.docs
        logger.info(f"Total documents in docstore: {len(docs)}")
        analyze_documents(docs)
    else:
        logger.warning("Unknown docstore structure")
        if hasattr(docstore, '__dict__'):
            for attr in dir(docstore):
                if not attr.startswith('_'):
                    try:
                        attr_value = getattr(docstore, attr, None)
                        logger.info(f"  docstore.{attr}: {type(attr_value)}")
                        if hasattr(attr_value, '__len__'):
                            logger.info(f"    Length: {len(attr_value)}")
                    except:
                        logger.info(f"  docstore.{attr}: <could not access>")

def analyze_documents(docs_dict):
    """Analyze documents from the docstore"""
    if not docs_dict:
        logger.warning("No documents found")
        return
    
    # File statistics
    file_stats = defaultdict(lambda: {'chunks': 0, 'total_chars': 0, 'doc_ids': []})
    metadata_fields = set()
    
    logger.info("Analyzing document contents...")
    
    for doc_id, document in docs_dict.items():
        # Check document structure
        if hasattr(document, 'metadata'):
            metadata = document.metadata
            metadata_fields.update(metadata.keys())
            filename = metadata.get('file_name', metadata.get('source', 'Unknown'))
        else:
            filename = 'Unknown'
            metadata = {}
        
        # Get content
        if hasattr(document, 'page_content'):
            content = document.page_content
        elif hasattr(document, 'content'):
            content = document.content
        else:
            content = str(document)
        
        # Update statistics
        file_stats[filename]['chunks'] += 1
        file_stats[filename]['total_chars'] += len(content)
        file_stats[filename]['doc_ids'].append(doc_id)
    
    # Report results
    logger.info("\n" + "="*60)
    logger.info("FILE ANALYSIS RESULTS")
    logger.info("="*60)
    
    for filename, stats in sorted(file_stats.items()):
        logger.info(f"\nFile: {filename}")
        logger.info(f"  Chunks: {stats['chunks']}")
        logger.info(f"  Total characters: {stats['total_chars']:,}")
        if stats['chunks'] > 0:
            logger.info(f"  Average chunk size: {stats['total_chars'] // stats['chunks']:,} chars")
        logger.info(f"  Doc IDs: {stats['doc_ids'][:5]}{'...' if len(stats['doc_ids']) > 5 else ''}")
    
    # Show metadata fields
    logger.info(f"\nMetadata fields found: {sorted(metadata_fields)}")
    
    # Show sample documents
    show_sample_documents(docs_dict, 3)

def show_sample_documents(docs_dict, num_samples=3):
    """Show sample documents"""
    logger.info(f"\nShowing {num_samples} sample documents:")
    logger.info("-" * 50)
    
    count = 0
    for doc_id, document in docs_dict.items():
        if count >= num_samples:
            break
        
        logger.info(f"\nSample {count + 1}:")
        logger.info(f"  Doc ID: {doc_id}")
        
        # Get metadata
        if hasattr(document, 'metadata'):
            logger.info(f"  Metadata: {document.metadata}")
        
        # Get content
        if hasattr(document, 'page_content'):
            content = document.page_content
        elif hasattr(document, 'content'):
            content = document.content
        else:
            content = str(document)
        
        # Show preview
        content_preview = content[:200]
        if len(content) > 200:
            content_preview += "..."
        logger.info(f"  Content preview: {repr(content_preview)}")
        logger.info(f"  Full content length: {len(content)} characters")
        
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

def main():
    """Main test function"""
    # Initialize logging
    setup_logging()
    global logger
    logger = get_logger(__name__)
    
    logger.info("Starting simple vectorstore contents test")
    logger.info("="*60)
    
    # Read pickle file directly
    data = read_vectorstore_pickle()
    if not data:
        logger.error("Cannot continue without pickle data")
        return
    
    # Analyze the data
    analyze_pickle_data(data)
    
    # Check PII mappings
    check_pii_mappings()
    
    logger.info("\n" + "="*60)
    logger.info("Simple vectorstore contents test completed")
    logger.info("="*60)

if __name__ == "__main__":
    main() 