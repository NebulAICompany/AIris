# %pip install prometheus_client
from prometheus_client import Counter, Histogram, start_http_server

api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
     ["status"]
)

llm_duration_seconds = Histogram(
    "llm_duration_seconds",
    "Duration of LLM requests in seconds",
    buckets=[0.1, 0.3, 0.5, 1, 2, 3, 5])

guard_violations_total = Counter(
    "guard_violations_total",
    "Total number of guard violations",
    ["violation_type"]
)

def expose_metrics(port=9090):
    """
    Start the Prometheus metrics server.
    """
    print(f"Starting metrics server on port {port}...")
    start_http_server(port)
    print(f"Metrics server started on port {port} and Metrics available at http://localhost:{port}/metrics")