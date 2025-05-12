from typing import List, Dict, Any  
import logging
from sentence_transformers import CrossEncoder


# Gereksiz uyarıları bastırmak için
logging.basicConfig(level=logging.INFO)
logging.getLogger("transformer").setLevel(logging.ERROR)

# Model önbelleği, modelin yalnızca bir kez yüklenmesini sağlar
_reranker_model_cache = {}

def _load_model(model_name: str) -> CrossEncoder:
    
    if model_name not in _reranker_model_cache:
        try:
            logging.info(f"Loading reranker model: {model_name}")
            _reranker_model_cache[model_name] = CrossEncoder(model_name)
            logging.info(f"Model loaded: {model_name}")
        except Exception as e:
            logging.error(f"Error loading model {model_name}: {e}")
            raise RuntimeError(f"Failed to load model {model_name}") from e
    
    return _reranker_model_cache[model_name]

def rerank(query: str, documents: List[str], with_score: bool = True , model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", top_n: int = 3) -> List[str]:
    if not documents:
        return []
    
    try : 
        model = _load_model(model_name)
        pairs = [[query, doc] for doc in documents]
        print(f"Pairs: {pairs}")
        scores = model.predict(pairs, show_progress_bar=True)
        reranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        top_docs = [doc for doc, _ in reranked[:top_n]]
        print(f"Top documents: {top_docs}")
        if with_score:
            return [{"content": doc, "score": float(score)} for doc, score in reranked[:top_n]]
        else:
            return top_docs
    
    except ImportError as e:
        logging.error(f"Error importing model {model_name}: {e}")
        raise RuntimeError(f"Failed to import model {model_name}") from e
    except Exception as e:
        logging.error(f"Error during reranking: {e}")
        raise RuntimeError("Reranking failed") from e
    