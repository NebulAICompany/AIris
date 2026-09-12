import subprocess
import os
from backend.shared.constants import FRONTEND_DIR

if __name__ == "__main__":
    # Change to frontend directory
    os.chdir(str(FRONTEND_DIR))
    # Start npm run dev command
    process = subprocess.Popen(["npm", "run", "dev"], shell=True)
    process.communicate()
