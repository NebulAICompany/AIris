import subprocess
import os

api_key = os.getenv("API_KEY", "test-key")

cmd = [
    "vllm", "serve", "zai-org/GLM-4.5V",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--api-key", api_key,
    "--tensor-parallel-size", "1",
    "--tool-call-parser", "glm45",
    "--reasoning-parser", "glm45",
    "--enable-auto-tool-choice",
    "--served-model-name", "glm-4.5v",
    "--allowed-local-media-path", "/",
    "--media-io-kwargs", '{"video": {"num_frames": -1}}',
    "--gpu-memory-utilization", "0.8",
    "--max-model-len", "4096"
]

subprocess.run(cmd)
