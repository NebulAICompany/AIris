#!/usr/bin/env python3
"""
Backend startup script for AIris application.
Run this from the aiirs directory: python start_backend.py
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path so aiiris_backend module can be found
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set environment variables
os.environ["PYTHONPATH"] = str(current_dir)

if __name__ == "__main__":
    import uvicorn
    
    # Start the server
    uvicorn.run(
        "aiiris_backend.app.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        reload_dirs=[str(current_dir / "aiiris_backend")]
    ) 