# Pre-embedding Process Selection System

## Overview

The AIris RAG system now features a configurable pre-embedding process selection system that allows you to choose between different document enhancement techniques before embedding. This system provides flexibility to optimize retrieval quality based on your specific use case and requirements.

## Available Pre-embedding Processes

### 1. None (`"none"`)
- **Description**: No pre-embedding processing applied
- **Use Case**: Simple documents, fast processing, minimal overhead
- **Benefits**: Fastest processing, lowest storage requirements
- **Drawbacks**: No enhancement to retrieval quality

### 2. HyPE (`"hype"`)
- **Description**: Hypothetical Prompt Embeddings - generates hypothetical questions/queries for each chunk
- **Use Case**: Improving query-document matching, especially for complex queries
- **Benefits**: Better query-document alignment, improved retrieval for specific questions
- **Drawbacks**: Increased processing time, higher storage requirements

### 3. CCH (`"cch"`)
- **Description**: Contextual Chunk Headers (AutoContext) - adds document and section context to chunks
- **Use Case**: Complex documents with hierarchical structure, preserving document context
- **Benefits**: Up to 84% reduction in retrieval failure rates, better context preservation
- **Drawbacks**: Highest processing time, requires LLM API calls

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Document      │    │  Pre-embedding   │    │   Vectorstore   │
│   Upload        │───▶│    Process       │───▶│   & Embeddings  │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Process Options   │
                    │                     │
                    │  • None (Standard)  │
                    │  • HyPE             │
                    │  • CCH (AutoContext)│
                    └─────────────────────┘
```

## API Usage

### Upload Endpoint

```bash
# Upload with no pre-embedding process
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "preEmbeddingProcess=none"

# Upload with HyPE
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "preEmbeddingProcess=hype"

# Upload with CCH (AutoContext)
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "preEmbeddingProcess=cch"
```

### Query Endpoint

```json
{
    "query": "What is the revenue for Q3?",
    "webSearchEnabled": false,
    "wolframEnabled": false,
    "ragFusionEnabled": false,
    "preEmbeddingProcess": "cch",
    "sessionId": "optional-session-id",
    "selectedFiles": ["optional-file-filter"]
}
```

## Code Examples

### 1. Using VectorStorePipeline Directly

```python
from aiiris_backend.pipelines.vectorpipe import VectorStorePipeline, PreEmbeddingProcess

# None process
pipeline_none = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.NONE)

# HyPE process
pipeline_hype = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.HYPE)

# CCH process
pipeline_cch = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.CCH)

# Run processing
pipeline_cch.run(
    uploads_path="path/to/uploads",
    save_path="path/to/vectorstore",
    specific_file="document.txt"
)
```

### 2. Legacy Compatibility

```python
from aiiris_backend.pipelines.vectorpipe import HyPEVectorStorePipeline

# Legacy HyPE pipeline (backward compatibility)
legacy_pipeline = HyPEVectorStorePipeline(autocontext_enabled=False)  # Uses HyPE
legacy_pipeline_with_cch = HyPEVectorStorePipeline(autocontext_enabled=True)  # Uses CCH

legacy_pipeline.run(
    uploads_path="path/to/uploads",
    save_path="path/to/vectorstore"
)
```

### 3. Upload Orchestrator Integration

```python
from aiiris_backend.orchestrator.upload_orchestrator import process_file

# Process with different pre-embedding processes
result_none = process_file("document.pdf", pre_embedding_process="none")
result_hype = process_file("document.pdf", pre_embedding_process="hype")
result_cch = process_file("document.pdf", pre_embedding_process="cch")
```

## Configuration Details

### PreEmbeddingProcess Enum

```python
from enum import Enum

class PreEmbeddingProcess(Enum):
    NONE = "none"
    HYPE = "hype"
    CCH = "cch"  # Contextual Chunk Headers (AutoContext)
```

### Parameter Conversion

The system automatically converts string parameters to enum values:

```python
# API string -> Internal enum
"none" -> PreEmbeddingProcess.NONE
"hype" -> PreEmbeddingProcess.HYPE
"cch" -> PreEmbeddingProcess.CCH
```

## Performance Comparison

| Process | Processing Time | Storage Overhead | Retrieval Quality | API Calls |
|---------|----------------|------------------|-------------------|-----------|
| None    | Fastest        | Minimal          | Baseline          | None      |
| HyPE    | Medium         | Medium           | Good              | Medium    |
| CCH     | Slowest        | Highest          | Excellent         | High      |

## Decision Matrix

### Use None When:
- Simple documents with straightforward content
- Fast processing is critical
- Storage space is limited
- No complex queries expected

### Use HyPE When:
- Need better query-document matching
- Documents contain specific factual information
- Users ask varied questions about the same content
- Moderate processing time is acceptable

### Use CCH When:
- Complex documents with hierarchical structure
- Context preservation is critical
- Maximum retrieval quality is required
- Processing time is not a constraint

## Implementation Details

### Event Loop Handling

The system includes robust event loop handling for async operations:

```python
def run_autocontext():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Handle running loop with ThreadPoolExecutor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(apply_autocontext(docs, file_name=file_name, enabled=True))
                )
                return future.result()
        else:
            return loop.run_until_complete(
                apply_autocontext(docs, file_name=file_name, enabled=True)
            )
    except RuntimeError:
        # Create new event loop if none exists
        return asyncio.run(apply_autocontext(docs, file_name=file_name, enabled=True))
```

### Error Handling

The system includes comprehensive error handling:

- Graceful fallback to original chunks if processing fails
- Detailed error logging for debugging
- Continuation of processing with warnings

### Logging

Processing is logged with detailed information:

```
🚀 Starting vector store processing with pre-embedding process: cch
🔗 Applying Contextual Chunk Headers (AutoContext) to document.txt...
✅ Contextual Chunk Headers applied to 15 chunks
```

## Testing

### Running Tests

```bash
# Run the pre-embedding process test suite
python test_pre_embedding_process.py
```

### Test Coverage

The test suite covers:
- None process functionality
- HyPE process functionality
- CCH process functionality
- Legacy pipeline compatibility
- API parameter conversion
- Error handling scenarios

## Migration Guide

### From Legacy AutoContext

```python
# Old way
pipeline = VectorStorePipeline(autocontext_enabled=True)

# New way
pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.CCH)
```

### From Legacy HyPE

```python
# Old way
pipeline = HyPEVectorStorePipeline()

# New way
pipeline = VectorStorePipeline(pre_embedding_process=PreEmbeddingProcess.HYPE)
```

### API Parameter Changes

```python
# Old API request
{
    "autoContextEnabled": true
}

# New API request
{
    "preEmbeddingProcess": "cch"
}
```

## Troubleshooting

### Common Issues

1. **Event Loop Errors**
   - Fixed with improved event loop handling
   - Automatic fallback to new event loop creation

2. **API Key Issues**
   - Ensure OPENAI_API_KEY is set for HyPE and CCH processes
   - Check API quotas and rate limits

3. **Processing Failures**
   - System falls back to original chunks with warnings
   - Check logs for detailed error information

### Performance Optimization

1. **Choose Appropriate Process**
   - Use None for simple documents
   - Use HyPE for better query matching
   - Use CCH for maximum quality

2. **Monitor Resource Usage**
   - CCH requires most memory and API calls
   - HyPE has moderate resource requirements
   - None has minimal overhead

## Future Enhancements

### Planned Features

1. **Hybrid Processing**: Combine multiple pre-embedding processes
2. **Adaptive Selection**: Automatically choose process based on document type
3. **Custom Processes**: User-defined pre-embedding processes
4. **Performance Caching**: Cache processed results for repeated use

### Integration Opportunities

- Document type detection for automatic process selection
- Quality metrics for process effectiveness measurement
- A/B testing framework for process comparison

## Best Practices

1. **Document Analysis**: Analyze your documents to choose the best process
2. **Performance Testing**: Test different processes with your specific use case
3. **Monitoring**: Monitor retrieval quality and processing performance
4. **Gradual Migration**: Migrate from legacy systems gradually
5. **Resource Planning**: Plan for increased resource usage with enhanced processes

## References

- [AutoContext Implementation](AUTOCONTEXT_README.md)
- [HyPE Documentation](https://example.com/hype)
- [dsRAG Repository](https://github.com/D-Star-AI/dsRAG)
- [Anthropic Research](https://www.anthropic.com)

## Contributing

To contribute to the pre-embedding process system:

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add comprehensive tests
5. Update documentation
6. Submit a pull request

## License

This implementation is part of the AIris RAG system and follows the project's licensing terms. 