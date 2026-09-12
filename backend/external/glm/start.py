import subprocess
import os
import sys


def main():
    print("🚀 Starting GLM-4.5V Vision Language Model...")
    print("=" * 50)

    # Environment variables
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("API_KEY is not set. Refusing to start with a default key.")
        sys.exit(1)
    port = os.getenv("PORT", "8080")  # Cloud Run PORT variable

    print(f"Port: {port}")
    print("API Key: configured")
    print(f"Model Cache: {os.getenv('HF_HOME', '/tmp/model_cache')}")
    print("=" * 50)

    # vLLM server command with all GLM-4.5V optimizations
    cmd = [
        "vllm",
        "serve",
        "zai-org/GLM-4.5V",
        "--host",
        "0.0.0.0",
        "--port",
        port,
        "--api-key",
        api_key,
        "--tensor-parallel-size",
        "1",
        "--tool-call-parser",
        "glm45",
        "--reasoning-parser",
        "glm45",
        "--enable-auto-tool-choice",
        "--served-model-name",
        "glm-4.5v",
        "--allowed-local-media-path",
        "/",
        "--media-io-kwargs",
        '{"video": {"num_frames": -1}}',
        "--gpu-memory-utilization",
        "0.85",
        "--max-model-len",
        "4096",
        "--download-dir",
        "/tmp/model_cache",
        "--trust-remote-code",
        "--disable-log-stats",
        "--quantization",
        "fp8",  # Memory optimization
    ]

    print("📦 Downloading and starting GLM-4.5V model...")
    print(f"⚡ Command: vllm serve zai-org/GLM-4.5V --host 0.0.0.0 --port {port} ...")
    print("⏳ This operation may take 15-25 minutes (first time)")
    print("=" * 50)

    try:
        # Start vLLM server
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"❌ Server startup error: {e}")
        print("💡 Check logs: Cloud Console > Cloud Run > Service Logs")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
