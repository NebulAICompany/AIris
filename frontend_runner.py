import subprocess
import os

if __name__ == "__main__":
    # frontend klasörüne geç
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    os.chdir(frontend_dir)
    # npm run dev komutunu başlat
    process = subprocess.Popen(["npm", "run", "dev"], shell=True)
    process.communicate()
