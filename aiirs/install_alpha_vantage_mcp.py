#!/usr/bin/env python3
"""
Alpha Vantage MCP Server Kurulum Script'i
Bu script Alpha Vantage MCP server'ını klonlar ve kurar.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, cwd=None):
    """Komut çalıştır ve sonucu döndür"""
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, cwd=cwd
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Komut hatası: {e}")
        print(f"STDERR: {e.stderr}")
        return None


def main():
    print("🚀 Alpha Vantage MCP Server Kurulumu Başlıyor...")

    # Proje ana dizini
    project_root = Path(__file__).parent
    mcp_dir = project_root / "alpha-vantage-mcp"

    print(f"📁 Proje dizini: {project_root}")
    print(f"📁 MCP dizini: {mcp_dir}")

    # 1. Repo'yu klonla
    if not mcp_dir.exists():
        print("📥 Alpha Vantage MCP repo'su klonlanıyor...")
        result = run_command(
            "git clone https://github.com/berlinbra/alpha-vantage-mcp.git",
            cwd=project_root,
        )
        if result is None:
            print("❌ Repo klonlanamadı!")
            return False
        print("✅ Repo başarıyla klonlandı")
    else:
        print("✅ Repo zaten mevcut")

    # 2. Virtual environment oluştur
    print("🐍 Virtual environment oluşturuluyor...")
    venv_path = mcp_dir / "venv"
    if not venv_path.exists():
        result = run_command(f"python -m venv {venv_path}", cwd=mcp_dir)
        if result is None:
            print("❌ Virtual environment oluşturulamadı!")
            return False
        print("✅ Virtual environment oluşturuldu")
    else:
        print("✅ Virtual environment zaten mevcut")

    # 3. Bağımlılıkları yükle
    print("📦 Bağımlılıklar yükleniyor...")

    # Python executable path
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"

    # pip upgrade
    result = run_command(f"{pip_exe} install --upgrade pip", cwd=mcp_dir)
    if result is None:
        print("❌ pip güncellenemedi!")
        return False

    # requirements yükle
    if (mcp_dir / "requirements.txt").exists():
        result = run_command(f"{pip_exe} install -r requirements.txt", cwd=mcp_dir)
    elif (mcp_dir / "pyproject.toml").exists():
        result = run_command(f"{pip_exe} install -e .", cwd=mcp_dir)
    else:
        # Manuel yükleme
        result = run_command(f"{pip_exe} install httpx mcp python-dotenv", cwd=mcp_dir)

    if result is None:
        print("❌ Bağımlılıklar yüklenemedi!")
        return False
    print("✅ Bağımlılıklar başarıyla yüklendi")

    # 4. Environment dosyası oluştur
    env_file = mcp_dir / ".env"
    if not env_file.exists():
        print("🔐 .env dosyası oluşturuluyor...")
        with open(env_file, "w") as f:
            f.write("# Alpha Vantage API Key\n")
            f.write("ALPHA_VANTAGE_API_KEY=your_api_key_here\n")
        print(f"✅ .env dosyası oluşturuldu: {env_file}")
        print("⚠️  Lütfen .env dosyasına Alpha Vantage API key'inizi ekleyin!")
    else:
        print("✅ .env dosyası zaten mevcut")

    # 5. Alpha vantage agent dosyasını güncelle
    print("🔧 Alpha Vantage agent dosyası güncelleniyor...")
    agent_file = (
        project_root / "aiiris_backend" / "agent_mcps" / "alpha_vantage_agent.py"
    )

    # Yolu güncelle
    with open(agent_file, "r", encoding="utf-8") as f:
        content = f.read()

    updated_content = content.replace(
        'cwd": "/path/to/alpha-vantage-mcp"', f'cwd": "{mcp_dir.absolute()}"'
    )

    with open(agent_file, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print("✅ Agent dosyası güncellendi")

    # 6. Test et
    print("🧪 MCP server test ediliyor...")
    test_command = f"{python_exe} -c \"import src.alpha_vantage_mcp.server; print('✅ MCP server import başarılı')\""
    result = run_command(test_command, cwd=mcp_dir)

    if result:
        print("✅ MCP server başarıyla test edildi")
    else:
        print("⚠️  MCP server test edilemedi, manuel kontrol edin")

    print("\n🎉 Alpha Vantage MCP Server kurulumu tamamlandı!")
    print("\n📋 Sonraki adımlar:")
    print(
        "1. https://www.alphavantage.co/support/#api-key adresinden ücretsiz API key alın"
    )
    print(f"2. {env_file} dosyasına API key'inizi ekleyin")
    print("3. Sistemi yeniden başlatın")

    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
