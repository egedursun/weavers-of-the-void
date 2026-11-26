import shutil
import sys
import time

print("Open https://example.test/oauth?code=true", flush=True)
print("Paste code here:", flush=True)
code = sys.stdin.readline().strip()
print("Your token:", flush=True)
print(f"sk-ant-oat01-abc{code}DEF-ghi" if shutil.get_terminal_size().columns >= 200 else "narrow", flush=True)
print("Store this token securely.", flush=True)
time.sleep(5)
