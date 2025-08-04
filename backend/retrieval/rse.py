import numpy as np
from typing import List, Dict, Any, Tuple
from backend.shared.logger import get_logger

logger = get_logger("RSE")

def get_best_segments(all_relevance_values: list[list], document_splits: list[int], max_length: int, overall_max_length: int, minimum_value: float):
    """
    This function takes the chunk relevance values and then runs an optimization algorithm to find the best segments.

    - all_relevance_values: a list of lists of relevance values for each chunk of a meta-document, with each outer list representing a query
    - document_splits: a list of indices that represent the start of each document - best segments will not overlap with these

    Returns
    - best_segments: a list of tuples (start, end) that represent the indices of the best segments (the end index is non-inclusive) in the meta-document
    - scores: a list of the scores for each of the best segments
    """
    best_segments = []
    scores = []
    total_length = 0
    rv_index = 0
    bad_rv_indices = []
    
    while total_length < overall_max_length:
        # cycle through the queries
        if rv_index >= len(all_relevance_values):
            rv_index = 0
        # if none of the queries have any more valid segments, we're done
        if len(bad_rv_indices) >= len(all_relevance_values):
            break        
        # check if we've already determined that there are no more valid segments for this query - if so, skip it
        if rv_index in bad_rv_indices:
            rv_index += 1
            continue
        
        # find the best remaining segment for this query
        relevance_values = all_relevance_values[rv_index] # get the relevance values for this query
        best_segment = None
        best_value = -1000
        
        for start in range(len(relevance_values)):
            # skip over negative value starting points
            if relevance_values[start] < 0:
                continue
            for end in range(start+1, min(start+max_length+1, len(relevance_values)+1)):
                # skip over negative value ending points
                if relevance_values[end-1] < 0:
                    continue
                # check if this segment overlaps with any of the best segments
                if any(start < seg_end and end > seg_start for seg_start, seg_end in best_segments):
                    continue
                # check if this segment overlaps with any of the document splits
                if any(start < split and end > split for split in document_splits):
                    continue
                # check if this segment would push us over the overall max length
                if total_length + end - start > overall_max_length:
                    continue
                segment_value = sum(relevance_values[start:end]) # define segment value as the sum of the relevance values of its chunks
                if segment_value > best_value:
                    best_value = segment_value
                    best_segment = (start, end)
        
        # if we didn't find a valid segment, mark this query as done
        if best_segment is None or best_value < minimum_value:
            bad_rv_indices.append(rv_index)
            rv_index += 1
            continue

        # otherwise, add the segment to the list of best segments
        best_segments.append(best_segment)
        scores.append(best_value)
        total_length += best_segment[1] - best_segment[0]
        rv_index += 1
    
    return best_segments, scores

def derive_chunk_index(result: dict):
    """Derive chunk index from metadata"""
    chunk_index = result["metadata"].get("chunk_index")
    if chunk_index is None:
        chunk_id = result["metadata"].get("chunk_id", "")
        if "chunk_" in chunk_id:
            try:
                chunk_index = int(chunk_id.split("chunk_")[1].split("_")[0])
            except (ValueError, IndexError):
                chunk_index = 0  # fallback
        else:
            chunk_index = 0
    else:
        chunk_index = int(chunk_index)
    return chunk_index

def get_meta_document(all_ranked_results: list[list], top_k_for_document_selection: int):
    """Create meta-document from top results across all queries"""
    # get the top_k results for each query - and the document IDs for the top results across all queries
    top_document_ids = []
    for ranked_results in all_ranked_results:
        for result in ranked_results[:top_k_for_document_selection]:
            # Handle current metadata format: file_name as doc_id
            document_id = result["metadata"].get("doc_id") or result["metadata"].get("file_name")
            if document_id:
                top_document_ids.append(document_id)
    unique_document_ids = list(set(top_document_ids)) # get the unique document IDs for the top results across all queries

    # get the max chunk index for each document and use this to get the document splits and document start points for the meta-document (i.e. the concatenation of all the documents)
    document_splits = [] # indices that represent the (non-inclusive) end of each document in the meta-document
    document_start_points = {} # index of the first chunk of each document in the meta-document, keyed on document_id
    
    for document_id in unique_document_ids:
        max_chunk_index = -1
        for ranked_results in all_ranked_results:
            for result in ranked_results:
                result_doc_id = result["metadata"].get("doc_id") or result["metadata"].get("file_name")
                if result_doc_id == document_id:
                    # Derive chunk index from metadata
                    chunk_index = derive_chunk_index(result)
                    max_chunk_index = max(max_chunk_index, chunk_index)
        document_start_points[document_id] = document_splits[-1] if document_splits else 0
        document_splits.append(int(max_chunk_index + document_splits[-1] + 1 if document_splits else max_chunk_index + 1)) # basically the start point of the next document

    return document_splits, document_start_points, unique_document_ids

def get_chunk_value(chunk_info: dict, irrelevant_chunk_penalty: float, decay_rate: int):
    """
    Calculate the value of a chunk based on rank and relevance.
    
    The irrelevant_chunk_penalty term has the effect of controlling how large of segments are created:
    - 0.05 gives very long segments of 20-50 chunks
    - 0.1 gives long segments of 10-20 chunks
    - 0.2 gives medium segments of 4-10 chunks
    - 0.3 gives short segments of 2-6 chunks
    - 0.4 gives very short segments of 1-3 chunks
    """
    rank = chunk_info.get('rank', 1000) # if rank is not provided, default to 1000
    absolute_relevance_value = chunk_info.get('absolute_relevance_value', 0.0) # if absolute_relevance_value is not provided, default to 0.0
    
    v = np.exp(-rank / decay_rate) * absolute_relevance_value - irrelevant_chunk_penalty
    return v

def get_relevance_values(all_ranked_results: list[list], meta_document_length: int, document_start_points: dict[str, int], unique_document_ids: list[str], irrelevant_chunk_penalty: float, decay_rate: int = 20, chunk_length_adjustment: bool = True):
    """Get relevance values for each chunk in the meta-document, separately for each query"""
    all_relevance_values = []
    
    for ranked_results in all_ranked_results:
        # loop through the top results for each query and add their rank to the relevance ranks list
        all_chunk_info = [{} for _ in range(meta_document_length)]
        
        for rank, result in enumerate(ranked_results):
            # Handle current metadata format: file_name as doc_id
            document_id = result["metadata"].get("doc_id") or result["metadata"].get("file_name")
            if document_id not in unique_document_ids:
                continue
            
            # For current format, derive chunk_index from chunk_id or use rank as fallback
            chunk_index = derive_chunk_index(result)
                
            meta_document_index = int(document_start_points[document_id] + chunk_index) # find the correct index for this chunk in the meta-document
            
            # Handle similarity score (prioritize score field from retriever)
            absolute_relevance_value = result.get("score", result.get("similarity", 0.0))
            # Convert similarity to positive relevance (FAISS returns negative distances)
            if absolute_relevance_value < 0:
                absolute_relevance_value = -absolute_relevance_value
            
            # Get chunk text from content or metadata
            chunk_text = result.get("content", result["metadata"].get("chunk_text", ""))
            chunk_length = len(chunk_text) # get the length of the chunk in characters
            
            all_chunk_info[meta_document_index] = {
                'rank': rank, 
                'absolute_relevance_value': absolute_relevance_value, 
                'chunk_length': chunk_length
            }

        # convert the relevance ranks and other info to chunk values
        relevance_values = [get_chunk_value(chunk_info, irrelevant_chunk_penalty, decay_rate) for chunk_info in all_chunk_info]

        if chunk_length_adjustment:
            # adjust the relevance values for the length of the chunks
            chunk_lengths = [chunk_info.get('chunk_length', 0.0) for chunk_info in all_chunk_info]
            relevance_values = adjust_relevance_values_for_chunk_length(relevance_values, chunk_lengths)

        all_relevance_values.append(relevance_values)
    
    return all_relevance_values

def adjust_relevance_values_for_chunk_length(relevance_values: list[float], chunk_lengths: list[int], reference_length: int = 700):
    """
    Scale the chunk values by chunk length relative to the reference length
    - reference_length is the length of a standard chunk, measured in number of characters (default is 700 characters, because this is the average length of a chunk when you set the max to 800, which is the default.)
    """
    assert len(relevance_values) == len(chunk_lengths), "The length of relevance_values and chunk_lengths must be the same"
    adjusted_relevance_values = []
    
    for relevance_value, chunk_length in zip(relevance_values, chunk_lengths):
        bounded_chunk_length = max(chunk_length, reference_length) # only adjust relevance values for chunks that are longer than the reference length
        adjusted_relevance_values.append(relevance_value * (bounded_chunk_length / reference_length))
    
    return adjusted_relevance_values

def apply_rse(all_ranked_results: List[List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], List[float]]:
    """
    Apply Relevant Segment Extraction to improve RAG retrieval.
    
    Args:
        all_ranked_results: List of lists of ranked results for each query
        
    Returns:
        Tuple of (selected_chunks, segment_scores)
    """
    if not all_ranked_results or not any(all_ranked_results):
        return [], []
    
    # Get RSE parameters
    params = {
        'max_length': 15,
        'overall_max_length': 30,
        'minimum_value': 0.5,
        'irrelevant_chunk_penalty': 0.18,
        'overall_max_length_extension': 5,
        'decay_rate': 30,
        'top_k_for_document_selection': 10,
        'chunk_length_adjustment': True,
    }
    
    # Step 1: Create meta-document
    document_splits, document_start_points, unique_document_ids = get_meta_document(
        all_ranked_results, params['top_k_for_document_selection']
    )
    
    if not unique_document_ids:
        return [], []
    
    # Calculate meta-document length
    meta_document_length = document_splits[-1] if document_splits else 0
    
    if meta_document_length == 0:
        return [], []
    
    # Step 2: Get relevance values
    all_relevance_values = get_relevance_values(
        all_ranked_results, 
        meta_document_length, 
        document_start_points, 
        unique_document_ids,
        params['irrelevant_chunk_penalty'],
        params['decay_rate'],
        params['chunk_length_adjustment']
    )
    
    # Step 3: Find best segments
    best_segments, scores = get_best_segments(
        all_relevance_values,
        document_splits,
        params['max_length'],
        params['overall_max_length'],
        params['minimum_value']
    )
    
    # Step 4: Extract the actual chunks for the best segments
    selected_chunks = []
    
    # Create a lookup for all chunks by their meta-document index
    chunk_lookup = {}
    for ranked_results in all_ranked_results:
        for result in ranked_results:
            document_id = result["metadata"].get("doc_id") or result["metadata"].get("file_name")
            if document_id in unique_document_ids:
                # Derive chunk index from metadata
                chunk_index = derive_chunk_index(result)
                meta_document_index = int(document_start_points[document_id] + chunk_index)
                chunk_lookup[meta_document_index] = result
    
    # Extract chunks for each best segment
    logger.debug(f"🧠 Best segments: {best_segments}")
    for segment_start, segment_end in best_segments:
        for idx in range(segment_start, segment_end):
            if idx in chunk_lookup:
                chunk = chunk_lookup[idx].copy()
                # Add RSE metadata
                chunk["metadata"] = chunk.get("metadata", {}).copy()
                chunk["metadata"]["rse_segment"] = True
                chunk["metadata"]["rse_segment_start"] = segment_start
                chunk["metadata"]["rse_segment_end"] = segment_end
                selected_chunks.append(chunk)
    
    return selected_chunks, scores

def apply_rse_single_query(ranked_results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[float]]:
    """
    Apply RSE to a single query's results by treating it as multiple queries.
    This is a fallback when we only have one query.
    """
    if not ranked_results:
        return [], []
    
    # For single query, we can create artificial "queries" by splitting the results
    # or use the same results multiple times with different focus
    all_ranked_results = [ranked_results]  # Simple approach: use the same results
    
    return apply_rse(all_ranked_results)

def retrieve_with_rse(query: str, k: int = 15) -> Tuple[List[Dict[str, Any]], List[float]]:
    """
    Retrieve documents using RSE enhancement.
    
    Args:
        query: The search query
        k: Number of initial documents to retrieve
        
    Returns:
        Tuple of (rse_enhanced_chunks, segment_scores)
    """
    from .retriever import retrieve_top_k
    
    # Get initial retrieval results
    initial_results = retrieve_top_k(query, k=k*3)
    unique_chunks = []
    duplicate_cleared_initial_results = []
    for r in initial_results:
        cid = r['metadata']['chunk_id'].split('_')[1]
        if cid not in unique_chunks:
            unique_chunks.append(cid)
            duplicate_cleared_initial_results.append(r)
    initial_results = duplicate_cleared_initial_results[:k]

    logger.debug(f"Initial Results: {[r['metadata']['chunk_id'] for r in duplicate_cleared_initial_results]}")
    
    if not duplicate_cleared_initial_results:
        return [], []
    
    # Apply RSE to single query results
    rse_chunks, scores = apply_rse_single_query(initial_results)
    sorted_rse_chunks = sorted(rse_chunks, key=lambda x: int(x['metadata']['chunk_id'].split('_')[1]))
    logger.debug(f"🧠 RSE Chunks: {sorted_rse_chunks}")
    logger.debug(f"initial results: {initial_results}")
    logger.debug(f"🧠 RSE Enhancement: {len(initial_results)} initial chunks → {len(rse_chunks)} optimized segments")
    if scores:
        logger.debug(f"📊 RSE Segment scores: {[f'{score:.3f}' for score in scores[:3]]}")
    
    return rse_chunks, scores 