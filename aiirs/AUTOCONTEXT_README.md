# AutoContext Implementation for AIris RAG System

## Overview

AutoContext (Contextual Chunk Headers) is a powerful RAG enhancement technique that significantly improves retrieval quality by adding contextual information to document chunks before embedding them. This implementation is based on the dsRAG approach and research from Anthropic, which demonstrated up to 84% reduction in retrieval failure rates.

## What is AutoContext?

AutoContext creates contextual chunk headers that contain document-level and section-level context, and prepends those chunk headers to the chunks prior to embedding them. This gives the embeddings a much more accurate and complete representation of the content and meaning of the text.

### Key Benefits

- **Dramatic Improvement in Retrieval Quality**: Up to 84% reduction in retrieval failure rates
- **Better Context Preservation**: Maintains document and section hierarchy information
- **Enhanced Semantic Understanding**: Embeddings capture more complete meaning
- **Reduced Irrelevant Results**: Fewer false positives in search results
- **Improved LLM Performance**: Better context leads to more accurate responses

## Architecture

The AutoContext system consists of several key components:

### 1. AutoContextProcessor
The main processor that handles document analysis and context generation:

```python
from aiiris_backend.retrieval.autocontext import AutoContextProcessor

processor = AutoContextProcessor(
    use_document_summary=True,
    use_section_summaries=True,
    document_title_guidance="Generate a concise, descriptive title",
    document_summary_guidance="Provide a brief summary of the document's main content",
    section_summary_guidance="Summarize the key points of this section"
)
```

### 2. Document Analysis Pipeline
- **Document Title Generation**: Creates descriptive titles for documents
- **Document Summarization**: Generates comprehensive document summaries
- **Section Hierarchy Extraction**: Identifies and analyzes document structure
- **Section Summarization**: Creates summaries for each document section

### 3. Contextual Header Creation
Combines document and section context into informative headers:

```
Context: Document: Machine Learning Fundamentals | Document Summary: This document covers the fundamentals of machine learning, including supervised, unsupervised, and reinforcement learning techniques. | Section: Types of Machine Learning | Section Summary: This section explains the three main categories of machine learning approaches.

Content: [Original chunk content]
```

## Implementation Details

### Core Files

1. **`aiiris_backend/retrieval/autocontext.py`**
   - Main AutoContext implementation
   - Document analysis and context generation
   - Section hierarchy extraction

2. **`aiiris_backend/pipelines/vectorpipe.py`**
   - Updated VectorStorePipeline with AutoContext support
   - Integration with existing chunking pipeline

3. **`aiiris_backend/orchestrator/upload_orchestrator.py`**
   - Updated to support AutoContext parameter
   - File processing with contextual enhancement

4. **`aiiris_backend/app/router.py`**
   - API endpoints updated with AutoContext parameter
   - Request models enhanced

### API Integration

#### Upload Endpoint
```python
POST /upload
Content-Type: multipart/form-data

file: [uploaded file]
autoContextEnabled: true/false
```

#### Query Endpoint
```python
POST /query
Content-Type: application/json

{
    "query": "What is machine learning?",
    "webSearchEnabled": false,
    "wolframEnabled": false,
    "ragFusionEnabled": false,
    "autoContextEnabled": true,
    "sessionId": "optional-session-id",
    "selectedFiles": ["optional-file-filter"]
}
```

## Usage Examples

### 1. Basic Usage

```python
from aiiris_backend.retrieval.autocontext import apply_autocontext
from langchain_core.documents import Document

# Create document chunks
chunks = [
    Document(page_content="Machine learning is a subset of AI...", metadata={"chunk_id": "1"}),
    Document(page_content="There are three main types...", metadata={"chunk_id": "2"})
]

# Apply AutoContext
enhanced_chunks = await apply_autocontext(
    chunks,
    document_title="Machine Learning Guide",
    file_name="ml_guide.txt",
    enabled=True
)
```

### 2. Vector Store Integration

```python
from aiiris_backend.pipelines.vectorpipe import VectorStorePipeline

# Create pipeline with AutoContext enabled
pipeline = VectorStorePipeline(autocontext_enabled=True)

# Process documents
pipeline.run(
    uploads_path="path/to/uploads",
    save_path="path/to/vectorstore",
    specific_file="document.txt"
)
```

### 3. File Upload with AutoContext

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "autoContextEnabled=true"
```

## Configuration Options

### AutoContextProcessor Parameters

- **`use_document_summary`**: Enable/disable document-level summarization
- **`use_section_summaries`**: Enable/disable section-level summarization
- **`document_title_guidance`**: Custom guidance for title generation
- **`document_summary_guidance`**: Custom guidance for document summarization
- **`section_summary_guidance`**: Custom guidance for section summarization

### Example Configuration

```python
processor = AutoContextProcessor(
    use_document_summary=True,
    use_section_summaries=True,
    document_title_guidance="Create a professional title that captures the document's purpose",
    document_summary_guidance="Summarize the key topics and objectives in 2-3 sentences",
    section_summary_guidance="Highlight the main points and concepts in this section"
)
```

## Performance Considerations

### Benefits
- **Improved Retrieval Accuracy**: Significantly better matching of user queries to relevant content
- **Enhanced Context Understanding**: Better preservation of document structure and meaning
- **Reduced False Positives**: Fewer irrelevant results in search responses

### Trade-offs
- **Increased Storage**: Contextual headers add overhead to chunk storage
- **Processing Time**: Additional LLM calls for context generation
- **API Costs**: More tokens processed for summarization

### Optimization Tips
1. **Selective Enablement**: Use AutoContext for complex documents where context is crucial
2. **Caching**: Consider caching generated summaries for frequently accessed documents
3. **Batch Processing**: Process multiple documents together when possible

## Testing

### Running Tests

```bash
# Run the AutoContext test suite
python test_autocontext.py
```

### Test Coverage
- Document title generation
- Document and section summarization
- Section hierarchy extraction
- Contextual header creation
- Integration with vectorization pipeline

### Expected Results
The test suite validates:
- Proper context generation
- Metadata preservation
- Performance metrics
- Error handling

## Monitoring and Metrics

### Key Metrics
- **Context Enhancement Ratio**: Average contextual size vs. original size
- **Processing Time**: Time taken for context generation
- **Retrieval Quality**: Improvement in search accuracy
- **Storage Overhead**: Additional space required for contextual headers

### Logging
AutoContext operations are logged with the "AUTOCONTEXT" context tag:
```
2024-01-01 10:00:00 - INFO - [AUTOCONTEXT] Processing 15 chunks with AutoContext
2024-01-01 10:00:05 - INFO - [AUTOCONTEXT] Generated document title: Machine Learning Fundamentals
2024-01-01 10:00:10 - INFO - [AUTOCONTEXT] Successfully processed 15 chunks with AutoContext
```

## Troubleshooting

### Common Issues

1. **LLM API Errors**
   - Check API keys and endpoints
   - Verify rate limits and quotas
   - Monitor network connectivity

2. **Memory Issues**
   - Reduce batch sizes for large documents
   - Consider processing documents individually
   - Monitor memory usage during processing

3. **Performance Issues**
   - Optimize chunk sizes
   - Use caching for repeated processing
   - Consider async processing for large batches

### Error Handling
The system includes robust error handling:
- Graceful fallback to original chunks if AutoContext fails
- Detailed error logging for debugging
- Retry mechanisms for transient failures

## Future Enhancements

### Planned Features
1. **Adaptive Context Generation**: Dynamic context based on document type
2. **Multi-language Support**: Context generation for non-English documents
3. **Custom Context Templates**: User-defined context formats
4. **Performance Optimization**: Caching and batch processing improvements

### Integration Opportunities
- **Semantic Sectioning**: Integration with advanced document structure analysis
- **Multi-modal Context**: Support for images, tables, and other content types
- **Domain-specific Context**: Specialized context for legal, medical, or technical documents

## References

- [dsRAG Repository](https://github.com/D-Star-AI/dsRAG) - Original AutoContext implementation
- [Anthropic Research](https://www.anthropic.com) - Contextual chunk headers research
- [Unstructured Platform](https://unstructured.io/blog/contextual-chunking-in-unstructured-platform-boost-your-rag-retrieval-accuracy) - Contextual chunking implementation

## Contributing

To contribute to the AutoContext implementation:

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add comprehensive tests
5. Update documentation
6. Submit a pull request

## License

This implementation is part of the AIris RAG system and follows the project's licensing terms. 