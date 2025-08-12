"""
Turkish-aware Keyword Search System using BM25 Algorithm
Integrates with existing vector search pipeline for hybrid retrieval
"""

import json
import math
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
import re

from backend.shared.logger import get_logger
from backend.shared.constants import VECTORSTORE_PATH_STR

logger = get_logger("KEYWORD_SEARCH")

# Turkish language processing with Hugging Face
try:
    from transformers import AutoTokenizer
    import torch
    
    # Use Turkish BERT tokenizer - dbmdz/bert-base-turkish-cased is well-maintained
    TURKISH_MODEL_NAME = "dbmdz/bert-base-turkish-cased"
    turkish_tokenizer = AutoTokenizer.from_pretrained(TURKISH_MODEL_NAME)
    
    TOKENIZER_AVAILABLE = True
    logger.info(f"✅ Turkish tokenizer loaded: {TURKISH_MODEL_NAME}")

except ImportError as e:
    turkish_tokenizer = None
    TOKENIZER_AVAILABLE = False
    logger.warning(f"⚠️ Transformers not available: {e}. Falling back to basic tokenization")
except Exception as e:
    turkish_tokenizer = None
    TOKENIZER_AVAILABLE = False
    logger.warning(f"⚠️ Failed to load Turkish tokenizer: {e}. Falling back to basic tokenization")


@dataclass
class SearchResult:
    """Represents a keyword search result"""
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    matched_terms: List[str]


class TurkishTextProcessor:
    """Handles Turkish text tokenization, normalization, and basic stemming"""
    
    def __init__(self):
        self.stop_words = self._load_turkish_stop_words()
        
    def _load_turkish_stop_words(self) -> Set[str]:
        """Load Turkish stop words"""
        # Comprehensive Turkish stop words
        stop_words = {
            # Most common stop words only - be less aggressive
            'bir', 'bu', 'şu', 'o', 'her', 'hiç', 
            # Most common prepositions
            'ile', 'için', 'gibi', 'göre', 'de', 'da', 'den', 'dan', 'te', 'ta',
            # Conjunctions
            've', 'veya', 'ama', 'fakat', 'hem',
            # Question particles
            'mi', 'mı', 'mu', 'mü',
            # Pronouns
            'ben', 'sen', 'biz', 'siz', 'onlar',
            # Very common words
            'olan', 'olarak', 'daha', 'en', 'çok', 'az', 'var', 'yok'
        }
        return stop_words
    
    def normalize_text(self, text: str) -> str:
        """Normalize Turkish text"""
        if not text:
            return ""
            
        # Remove HTML tags and attributes more thoroughly
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)  # Remove HTML entities
        
        # Remove excessive punctuation and special characters but keep Turkish chars
        text = re.sub(r'[^\w\sçğıöşüÇĞIİÖŞÜ.,!?%-]', ' ', text)
        
        # Convert to lowercase
        text = text.lower()
        
        # Clean up extra whitespace and normalize
        text = ' '.join(text.split())
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize Turkish text using Hugging Face tokenizer or fallback method"""
        if not text or not text.strip():
            return []
            
        if TOKENIZER_AVAILABLE and turkish_tokenizer:
            try:
                # Use Hugging Face tokenizer with truncation to handle long texts
                encoded = turkish_tokenizer(
                    text, 
                    add_special_tokens=False, 
                    return_tensors=None,
                    truncation=True,
                    max_length=1024,
                    padding=False
                )
                token_ids = encoded['input_ids']
                
                # Decode tokens back to get the actual token strings
                tokens = []
                for token_id in token_ids:
                    token_str = turkish_tokenizer.decode([token_id]).strip()
                    # Filter out subword markers and clean tokens
                    if token_str and not token_str.startswith('##') and len(token_str) > 1:
                        # Remove any remaining special characters but keep Turkish chars
                        clean_token = re.sub(r'[^\w\sçğıöşüÇĞIİÖŞÜ]', '', token_str).lower().strip()
                        if clean_token and len(clean_token) > 1:
                            tokens.append(clean_token)
                
                return tokens
                
            except Exception as e:
                logger.warning(f"Hugging Face tokenization failed: {e}, falling back to basic tokenization")
        
        # Fallback tokenization
        # Remove punctuation but keep Turkish characters
        text = re.sub(r'[^\w\sçğıöşüÇĞIİÖŞÜ]', ' ', text)
        tokens = [token.lower().strip() for token in text.split() if len(token.strip()) > 1]
        return tokens
    
    def simple_turkish_stem(self, word: str) -> str:
        """Simple Turkish stemming using common suffix removal"""
        if not word or len(word) <= 3:
            return word.lower()
        
        word = word.lower()
        
        # Common Turkish suffixes (ordered by length, longest first)
        suffixes = [
            # Plural + possessive combinations
            'larımız', 'lerimiz', 'larınız', 'leriniz', 'larının', 'lerinin',
            'larında', 'lerinde', 'larından', 'lerinden',
            # Possessive suffixes
            'imiz', 'ımız', 'umuz', 'ümüz', 'iniz', 'ınız', 'unuz', 'ünüz',
            'inin', 'ının', 'unun', 'ünün', 'inde', 'ında', 'unda', 'ünde',
            'inden', 'ından', 'undan', 'ünden',
            # Plural suffixes
            'lar', 'ler',
            # Case suffixes
            'den', 'dan', 'ten', 'tan', 'nin', 'nın', 'nun', 'nün',
            'nde', 'nda', 'nte', 'nta', 'nden', 'ndan', 'nten', 'ntan',
            # Personal suffixes
            'im', 'ım', 'um', 'üm', 'in', 'ın', 'un', 'ün',
            'si', 'sı', 'su', 'sü',
            # Locative/Ablative
            'de', 'da', 'te', 'ta', 'ye', 'ya', 'ne', 'na',
            # Copula
            'dir', 'dır', 'dur', 'dür', 'tir', 'tır', 'tur', 'tür',
            # Other common suffixes
            'ki', 'ca', 'ça', 'ce', 'çe', 'li', 'lı', 'lu', 'lü',
            'siz', 'sız', 'suz', 'süz'
        ]
        
        # Try to remove suffixes
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[:-len(suffix)]
        
        return word
    
    def process_text(self, text: str, use_stemming: bool = True) -> List[str]:
        """Complete text processing pipeline"""
        if not text:
            return []
            
        # Normalize text
        normalized_text = self.normalize_text(text)
        
        # Tokenize
        tokens = self.tokenize(normalized_text)
        
        # Filter stop words and very short tokens (be less aggressive)
        filtered_tokens = [
            token for token in tokens 
            if token not in self.stop_words and len(token) > 1 and not token.isdigit()
        ]
        
        # Apply simple stemming if requested
        if use_stemming:
            processed_tokens = [self.simple_turkish_stem(token) for token in filtered_tokens]
        else:
            processed_tokens = filtered_tokens
            
        # Return all tokens (including duplicates) for proper term frequency calculation
        # Filter out empty tokens but keep duplicates for BM25
        final_tokens = [token for token in processed_tokens if token]
                
        return final_tokens


class BM25KeywordSearch:
    """BM25-based keyword search with Turkish language support"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # Term frequency saturation parameter
        self.b = b    # Length normalization parameter
        
        self.text_processor = TurkishTextProcessor()
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.term_frequencies: Dict[str, Dict[str, int]] = {}
        self.document_frequencies: Dict[str, int] = defaultdict(int)
        self.document_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.total_documents: int = 0
        
        # File paths for persistence
        self.index_dir = Path(VECTORSTORE_PATH_STR) / "keyword_index"
        self.index_dir.mkdir(exist_ok=True)
        self.documents_file = self.index_dir / "documents.json"
        self.index_file = self.index_dir / "bm25_index.pkl"
        
        logger.info("🔍 BM25 Keyword Search initialized")
    
    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """Add a document to the search index"""
        if not content or not content.strip():
            logger.warning(f"⚠️ Skipping document {doc_id}: empty content")
            return
            
        # Process text to get terms
        terms = self.text_processor.process_text(content, use_stemming=False)
        if not terms:
            logger.warning(f"⚠️ Skipping document {doc_id}: no terms after processing")
            return
            
        # Store document
        self.documents[doc_id] = {
            'content': content,
            'metadata': metadata,
            'terms': terms
        }
        
        # Calculate term frequencies for this document
        term_freq = Counter(terms)
        self.term_frequencies[doc_id] = dict(term_freq)
        
        # Update document frequencies (how many docs contain each term)
        unique_terms = set(terms)
        for term in unique_terms:
            self.document_frequencies[term] += 1
            
        # Store document length
        self.document_lengths[doc_id] = len(terms)
        
        # Update total documents and average length
        self.total_documents = len(self.documents)
        if self.total_documents > 0:
            self.avg_doc_length = sum(self.document_lengths.values()) / self.total_documents
            
        logger.debug(f"✅ Added document {doc_id} with {len(terms)} terms (total: {self.total_documents})")
    
    def calculate_bm25_score(self, query_terms: List[str], doc_id: str) -> Tuple[float, List[str]]:
        """Calculate BM25 score for a document given query terms"""
        # logger.info(f"Calculating BM25 score for document {doc_id}")
        # logger.info(f"Query terms: {query_terms}")
        # logger.info(f"Term frequencies: {self.term_frequencies}")
        # logger.info(f"Document frequencies: {self.document_frequencies}")
        # logger.info(f"Document lengths: {self.document_lengths}")
        # logger.info(f"Average document length: {self.avg_doc_length}")
        if doc_id not in self.term_frequencies:
            return 0.0, []
            
        doc_tf = self.term_frequencies[doc_id]
        doc_length = self.document_lengths[doc_id]
        matched_terms = []
        score = 0.0
        
        for term in query_terms:
            if term in doc_tf:
                matched_terms.append(term)
                
                # Term frequency in document
                tf = doc_tf[term]
                
                # Document frequency (how many docs contain this term)
                df = self.document_frequencies.get(term, 0)
                
                if df == 0:
                    continue
                    
                # IDF calculation
                idf = math.log((self.total_documents - df + 0.5) / (df + 0.5))
                
                # BM25 formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
                
                term_score = idf * (numerator / denominator)
                score += term_score
                
        return score, matched_terms
    
    def search(self, query: str, k: int = 10, selected_files: Optional[List[str]] = None) -> List[SearchResult]:
        """Search documents using BM25 algorithm"""
        if not query or not query.strip():
            return []
            
        if self.total_documents == 0:
            logger.warning("No documents in keyword search index")
            return []
            
        logger.info(f"🔍 Keyword search for: '{query}' (limit: {k})")
        
        # Process query
        query_terms = self.text_processor.process_text(query, use_stemming=False)
        if not query_terms:
            logger.warning("No valid terms found in query after processing")
            return []
        
        logger.info(f"Query terms after processing: {query_terms}")
        logger.info(f"Selected files: {selected_files}")
        logger.info(f"Length of Documents: {len(self.documents)}")
        # Calculate scores for all documents
        scores = []
        for doc_id in self.documents:
            
            # Filter by selected files if specified
            if selected_files:
                doc_metadata = self.documents[doc_id]['metadata']
                file_name = doc_metadata.get('file_name', '')
                # Remove extension for comparison
                file_name_base = file_name.split('.')[0] if '.' in file_name else file_name
                logger.info(f"File name base: {file_name_base}")
                if file_name_base not in selected_files:
                    continue
            
            score, matched_terms = self.calculate_bm25_score(query_terms, doc_id)
            if score > 0:
                scores.append((doc_id, score, matched_terms))
        
        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Create search results
        results = []
        for doc_id, score, matched_terms in scores[:k]:
            doc_data = self.documents[doc_id]
            result = SearchResult(
                doc_id=doc_id,
                content=doc_data['content'],
                score=score,
                metadata=doc_data['metadata'],
                matched_terms=matched_terms
            )
            results.append(result)
        
        logger.info(f"✅ Found {len(results)} matching documents")
        return results
    
    def save_index(self):
        """Save the search index to disk"""
        try:
            # Save documents as JSON
            with open(self.documents_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
            
            # Save index data as pickle
            index_data = {
                'term_frequencies': self.term_frequencies,
                'document_frequencies': dict(self.document_frequencies),
                'document_lengths': self.document_lengths,
                'avg_doc_length': self.avg_doc_length,
                'total_documents': self.total_documents,
                'k1': self.k1,
                'b': self.b
            }
            
            with open(self.index_file, 'wb') as f:
                pickle.dump(index_data, f)
                
            logger.info(f"💾 Keyword search index saved ({self.total_documents} documents)")
            
        except Exception as e:
            logger.error(f"❌ Failed to save keyword search index: {e}")
    
    def load_index(self) -> bool:
        """Load the search index from disk"""
        try:
            if not self.documents_file.exists() or not self.index_file.exists():
                logger.info("No existing keyword search index found")
                return False
            
            # Load documents
            with open(self.documents_file, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            
            # Load index data
            with open(self.index_file, 'rb') as f:
                index_data = pickle.load(f)
                
            self.term_frequencies = index_data['term_frequencies']
            self.document_frequencies = defaultdict(int, index_data['document_frequencies'])
            self.document_lengths = index_data['document_lengths']
            self.avg_doc_length = index_data['avg_doc_length']
            self.total_documents = index_data['total_documents']
            self.k1 = index_data.get('k1', 1.5)
            self.b = index_data.get('b', 0.75)
            
            logger.info(f"📚 Keyword search index loaded ({self.total_documents} documents)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load keyword search index: {e}")
            return False
    
    def clear_index(self):
        """Clear the entire search index"""
        self.documents.clear()
        self.term_frequencies.clear()
        self.document_frequencies.clear()
        self.document_lengths.clear()
        self.avg_doc_length = 0.0
        self.total_documents = 0
        
        # Remove index files
        try:
            if self.documents_file.exists():
                self.documents_file.unlink()
            if self.index_file.exists():
                self.index_file.unlink()
            logger.info("🗑️ Keyword search index cleared")
        except Exception as e:
            logger.error(f"❌ Failed to clear index files: {e}")
    
    def remove_documents_by_file(self, file_name: str):
        """Remove all documents from a specific file"""
        docs_to_remove = []
        
        # Find all document IDs that start with the file name
        for doc_id in self.documents.keys():
            if doc_id.startswith(f"{file_name}_"):
                docs_to_remove.append(doc_id)
        
        if not docs_to_remove:
            logger.info(f"No existing documents found for file: {file_name}")
            return
            
        logger.info(f"🗑️ Removing {len(docs_to_remove)} existing documents for file: {file_name}")
        
        # Remove documents and their associated data
        for doc_id in docs_to_remove:
            # Remove from documents
            if doc_id in self.documents:
                del self.documents[doc_id]
            
            # Remove from term frequencies and update document frequencies
            if doc_id in self.term_frequencies:
                # Decrease document frequencies for each unique term in this document
                unique_terms = set(self.term_frequencies[doc_id].keys())
                for term in unique_terms:
                    if term in self.document_frequencies:
                        self.document_frequencies[term] -= 1
                        if self.document_frequencies[term] <= 0:
                            del self.document_frequencies[term]
                
                del self.term_frequencies[doc_id]
            
            # Remove from document lengths
            if doc_id in self.document_lengths:
                del self.document_lengths[doc_id]
        
        # Update total documents and average length
        self.total_documents = len(self.documents)
        if self.total_documents > 0:
            self.avg_doc_length = sum(self.document_lengths.values()) / self.total_documents
        else:
            self.avg_doc_length = 0.0
            
        logger.info(f"✅ Removed {len(docs_to_remove)} documents. Index now has {self.total_documents} documents")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics"""
        return {
            'total_documents': self.total_documents,
            'total_terms': len(self.document_frequencies),
            'avg_doc_length': self.avg_doc_length,
            'index_size_mb': self._get_index_size_mb()
        }
    
    def _get_index_size_mb(self) -> float:
        """Get index size in MB"""
        try:
            total_size = 0
            if self.documents_file.exists():
                total_size += self.documents_file.stat().st_size
            if self.index_file.exists():
                total_size += self.index_file.stat().st_size
            return total_size / (1024 * 1024)
        except:
            return 0.0


# Global keyword search instance
_keyword_search_instance = None

def get_keyword_search() -> BM25KeywordSearch:
    """Get or create the global keyword search instance"""
    global _keyword_search_instance
    if _keyword_search_instance is None:
        _keyword_search_instance = BM25KeywordSearch()
        _keyword_search_instance.load_index()
    return _keyword_search_instance


def keyword_search(query: str, k: int = 10, selected_files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Perform keyword search and return results in the same format as vector search
    
    Args:
        query: Search query
        k: Number of results to return
        selected_files: Optional list of files to search in
        
    Returns:
        List of search results compatible with existing retrieval system
    """
    search_engine = get_keyword_search()
    results = search_engine.search(query, k=k, selected_files=selected_files)
    
    # Convert to format compatible with existing retrieval system
    formatted_results = []
    for result in results:
        formatted_result = {
            'content': result.content,
            'score': result.score,
            'metadata': {
                **result.metadata,
                'match_type': 'keyword_match',
                'matched_terms': result.matched_terms,
                'search_method': 'bm25'
            }
        }
        formatted_results.append(formatted_result)
    
    return formatted_results

