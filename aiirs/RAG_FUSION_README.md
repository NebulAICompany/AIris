# RAG Fusion Implementation

## Overview

RAG Fusion is an advanced retrieval technique that enhances the traditional RAG (Retrieval-Augmented Generation) system by generating multiple related queries and using Reciprocal Rank Fusion (RRF) to combine and re-rank search results. This implementation improves the quality and comprehensiveness of retrieved documents for better AI responses.

## Key Features

### 1. **Multi-Query Generation**
- Automatically generates multiple related queries from a single user input
- Uses LLM to create diverse queries that approach the topic from different angles
- Supports multiple languages (English, Turkish, etc.)
- Configurable number of generated queries (default: 4)

### 2. **Reciprocal Rank Fusion (RRF)**
- Combines search results from multiple queries using RRF algorithm
- Reduces the impact of individual query biases
- Provides more comprehensive and balanced results
- Configurable RRF parameter (k=60 by default)

### 3. **Seamless Integration**
- Integrated with existing RAG pipeline
- Toggle-based enable/disable functionality
- Compatible with existing features (web search, Wolfram Alpha, file selection)
- Maintains backward compatibility

## Architecture

```
User Query → Query Generation → Multiple Queries → Vector Search → RRF → Final Reranking → Response
```

### Components

1. **Query Generator** (`generate_fusion_queries`)
   - Takes original query and generates related queries
   - Uses LLM with structured prompts
   - Handles multilingual queries

2. **Reciprocal Rank Fusion** (`reciprocal_rank_fusion`)
   - Combines search results from multiple queries
   - Applies RRF algorithm with configurable parameters
   - Handles document deduplication

3. **Retrieval Pipeline** (`retrieve_with_fusion`)
   - Orchestrates the complete RAG Fusion process
   - Integrates with existing vector store
   - Optional final reranking with Cohere

4. **UI Integration**
   - Toggle switch in header for easy enable/disable
   - Persistent settings storage
   - Multilingual UI support

## Usage

### Backend API

```python
from aiiris_backend.retrieval.rag_fusion import retrieve_with_fusion

# Use RAG Fusion for document retrieval
docs, metadata = await retrieve_with_fusion(
    query="What is artificial intelligence?",
    k=15,                    # Documents per query
    num_queries=4,           # Number of queries to generate
    rrf_k=60,               # RRF parameter
    final_rerank=True,      # Apply final reranking
    top_n=5                 # Final documents to return
)
```

### Query Orchestrator

```python
# Enable RAG Fusion in query orchestrator
response = await run_orchestration(
    query="Your question here",
    web_search_enabled=False,
    wolfram_enabled=False,
    rag_fusion_enabled=True,  # Enable RAG Fusion
    session_id=None,
    selected_files=None
)
```

### Frontend API

```javascript
// Send query with RAG Fusion enabled
const response = await window.apiService.sendQuery(
    "Your question here",
    false,  // webSearchEnabled
    false,  // wolframEnabled
    true,   // ragFusionEnabled
    null,   // sessionId
    null    // selectedFiles
);
```

## Configuration

### RAG Fusion Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `k` | 15 | Number of documents to retrieve per query |
| `num_queries` | 4 | Number of additional queries to generate |
| `rrf_k` | 60 | RRF parameter for score combination |
| `final_rerank` | true | Whether to apply final reranking |
| `top_n` | 5 | Final number of documents to return |

### Query Generation Prompt

The system uses a structured prompt to generate related queries:

```
You are a helpful assistant that generates multiple search queries based on a single input query.

Generate {num_queries} different search queries that are related to the original query but approach it from different angles or aspects.

Requirements:
- Generate exactly {num_queries} queries
- Each query should be different but related to the original
- Queries should be in the same language as the original query
- Focus on different aspects, synonyms, or related concepts
- Keep queries concise and searchable
```

## File Structure

```
aiiris_backend/
├── retrieval/
│   ├── rag_fusion.py          # Main RAG Fusion implementation
│   ├── retriever.py           # Vector store retrieval
│   └── reranker.py            # Document reranking
├── orchestrator/
│   └── query_orchestrator.py  # Integration with query orchestrator
└── app/
    └── router.py              # API endpoint updates

aiiris_ui/
├── src/
│   ├── renderer/
│   │   ├── index.html         # UI toggle
│   │   └── scripts/
│   │       ├── api.js         # API client updates
│   │       ├── components.js  # UI component updates
│   │       ├── utils.js       # Settings storage
│   │       └── language.js    # Translations
│   └── main.js                # IPC handler updates
└── styles/
    └── main.css               # Toggle styling
```

## Testing

Run the test suite to verify the implementation:

```bash
python test_rag_fusion.py
```

The test suite covers:
- Query generation functionality
- Reciprocal Rank Fusion algorithm
- Full RAG Fusion pipeline
- Integration with query orchestrator

## Performance Considerations

### Benefits
- **Improved Recall**: Multiple queries capture different aspects of the topic
- **Reduced Bias**: RRF reduces individual query biases
- **Better Relevance**: Combines strengths of multiple search approaches
- **Comprehensive Coverage**: Finds documents that might be missed by single queries

### Trade-offs
- **Increased Latency**: Multiple queries and processing steps
- **Higher Resource Usage**: More API calls and computation
- **Complexity**: More components to maintain and debug

### Optimization Tips
1. **Adjust Parameters**: Tune `k`, `num_queries`, and `rrf_k` based on your use case
2. **Caching**: Consider caching generated queries for similar inputs
3. **Parallel Processing**: The system already processes queries in parallel
4. **Monitoring**: Track performance metrics and adjust accordingly

## Troubleshooting

### Common Issues

1. **Query Generation Fails**
   - Check LLM API connectivity
   - Verify prompt template formatting
   - Ensure language service is available

2. **No Results After Fusion**
   - Check vector store connectivity
   - Verify document indexing
   - Adjust RRF parameters

3. **Performance Issues**
   - Reduce `num_queries` parameter
   - Optimize vector store configuration
   - Consider disabling final reranking

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features
1. **Adaptive Query Generation**: Adjust number of queries based on query complexity
2. **Query Quality Scoring**: Evaluate and filter generated queries
3. **Semantic Clustering**: Group similar queries to reduce redundancy
4. **Performance Caching**: Cache results for common query patterns
5. **Advanced RRF**: Implement weighted RRF based on query confidence

### Integration Opportunities
1. **Hybrid Search**: Combine with keyword search for better coverage
2. **User Feedback**: Learn from user interactions to improve query generation
3. **Domain-Specific Tuning**: Customize for financial document processing
4. **Multi-Modal Fusion**: Extend to image and other content types

## Contributing

When contributing to RAG Fusion:

1. **Follow Existing Patterns**: Use similar code structure as other retrieval modules
2. **Add Tests**: Include unit tests for new functionality
3. **Update Documentation**: Keep this README and code comments current
4. **Performance Testing**: Verify changes don't significantly impact performance
5. **UI Consistency**: Maintain consistent UI patterns for new features

## References

- [RAG Fusion Paper](https://github.com/Raudaschl/rag-fusion) - Original RAG Fusion concept
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) - RRF algorithm details
- [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) - Base RAG methodology

## License

This implementation is part of the AIris project and follows the same licensing terms. 