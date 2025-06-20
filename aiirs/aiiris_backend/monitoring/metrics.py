# %pip install prometheus_client
from prometheus_client import Counter, Histogram, start_http_server

api_requests_total = Counter(
    "api_requests_total", "Total number of API requests", ["status"]
)

llm_duration_seconds = Histogram(
    "llm_duration_seconds",
    "Duration of LLM requests in seconds",
    buckets=[0.1, 0.3, 0.5, 1, 2, 3, 5],
)

guard_violations_total = Counter(
    "guard_violations_total", "Total number of guard violations", ["violation_type"]
)

# HyPE indexing metrics
hype_indexing_duration_seconds = Histogram(
    "hype_indexing_duration_seconds",
    "Duration of HyPE indexing process in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

hype_hypothetical_content_generated = Counter(
    "hype_hypothetical_prompts_generated_total",
    "Total number of hypothetical prompts generated during indexing",
)

hype_enhanced_documents_indexed = Counter(
    "hype_enhanced_documents_indexed_total",
    "Total number of documents indexed with HyPE enhancements",
    ["content_type"],  # original or hypothetical_prompt
)

vectorstore_total_chunks = Histogram(
    "vectorstore_total_chunks",
    "Total number of chunks in vectorstore including HyPE prompt expansions",
    buckets=[10, 50, 100, 500, 1000, 5000, 10000],
)


def expose_metrics(port=9090):
    """
    Start the Prometheus metrics server.
    """
    print(f"Starting metrics server on port {port}...")
    start_http_server(port)
    print(
        f"Metrics server started on port {port} and Metrics available at http://localhost:{port}/metrics"
    )
