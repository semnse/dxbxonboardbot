"""Fix database connection and restart bot"""
import subprocess
import time
import os

print("="*70)
print("FIXING DATABASE CONNECTION")
print("="*70)

# 1. Kill all Python processes
print("\n[1/4] Stopping old processes...")
subprocess.run("taskkill /F /IM python.exe 2>nul", shell=True, capture_output=True)
time.sleep(2)

# 2. Set environment variable for asyncpg
print("[2/4] Setting environment variables...")
os.environ['PYTHONASYNCIODEBUG'] = '0'

# 3. Start uvicorn
print("[3/4] Starting uvicorn...")
proc = subprocess.Popen(
    "venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
    shell=True,
    cwd="e:\\Carrot1_WaitingClient"
)

# 4. Wait and check
print("[4/4] Waiting for startup...")
time.sleep(10)

# Check health
import urllib.request
try:
    response = urllib.request.urlopen("http://localhost:8000/")
    print(f"\n[OK] Application started! Status: {response.status}")
except Exception as e:
    print(f"\n[WARN] Health check failed: {e}")

print("\n" + "="*70)
print("NOW TEST IN TELEGRAM:")
print("  1. Write /start to bot")
print("  2. Write /add 6784 in chat")
print("="*70)
