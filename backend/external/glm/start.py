import subprocess
import os
import sys


def main():
    print("🚀 GLM-4.5V Vision Language Model başlatılıyor...")
    print("=" * 50)

    # Environment variables
    api_key = os.getenv("API_KEY", "test-key")
    port = os.getenv("PORT", "8080")  # Cloud Run PORT variable

    print(f"📡 Port: {port}")
    print(
        f"🔑 API Key: {api_key[:8]}{'*' * (len(api_key) - 8) if len(api_key) > 8 else '***'}"
    )
    print(f"🏠 Model Cache: {os.getenv('HF_HOME', '/tmp/model_cache')}")
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

    print("📦 GLM-4.5V model indiriliyor ve başlatılıyor...")
    print(f"⚡ Command: vllm serve zai-org/GLM-4.5V --host 0.0.0.0 --port {port} ...")
    print("⏳ Bu işlem 15-25 dakika sürebilir (ilk kez)")
    print("=" * 50)

    try:
        # Start vLLM server
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server durduruldu.")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"❌ Server başlatma hatası: {e}")
        print("💡 Log'ları kontrol edin: Cloud Console > Cloud Run > Service Logs")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
