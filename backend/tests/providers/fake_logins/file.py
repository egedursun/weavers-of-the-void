import sys
import time
from pathlib import Path

if not Path(".gemini/settings.json").exists():
    print("No authentication method selected.", flush=True)
    time.sleep(30)
print("Enter the authorization code:", flush=True)
sys.stdin.readline()
Path(".gemini").mkdir(exist_ok=True)
Path(".gemini/creds.json").write_text("{}", encoding="utf-8")
time.sleep(30)
