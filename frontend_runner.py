import subprocess
import os
from backend.shared.constants import FRONTEND_DIR

if __name__ == "__main__":
    # frontend klasörüne geç
    os.chdir(str(FRONTEND_DIR))
    # npm run dev komutunu başlat
    process = subprocess.Popen(["npm", "run", "dev"], shell=True)
    process.communicate()
