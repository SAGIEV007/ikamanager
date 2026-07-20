"""IkaManager - Run this file to start the application.

Usage:
    python run.py

Then open http://localhost:8000 in your browser.
"""
import subprocess
import sys
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

# Install dependencies if needed. onnxruntime is checked separately because it
# was added after the first release, so existing installs won't have it yet.
try:
    import fastapi
    import aiohttp
    import onnxruntime  # local captcha solver
except ImportError:
    print("Installing dependencies (pode demorar 1-2 min na primeira vez)...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
        "aiosqlite", "--quiet"
    ])

print("")
print("=" * 50)
print("  IkaManager is starting...")
print("  Open in your browser: http://localhost:8000")
print("=" * 50)
print("")

# Run the server
subprocess.call([
    sys.executable, "-m", "uvicorn", "app.main:app",
    "--host", "0.0.0.0", "--port", "8000"
])
