import argparse
import os
import platform
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
WORKER_DIR = ROOT / "image-worker"
RUN_DIR = ROOT / "data" / "run"
WORKER_PID = RUN_DIR / "image-worker.pid"
WORKER_LOG = RUN_DIR / "image-worker.log"
SECRET_KEY = "AERONA_MEDIA_SECRET_KEY"
SECRET_BYTES = 24
NATIVE_WORKER_URL = "http://127.0.0.1:8100"
DOCKER_HOST_WORKER_URL = "http://host.docker.internal:8100"
DOCKER_WORKER_URL = "http://image-worker:8100"
WORKER_HEALTH = f"{NATIVE_WORKER_URL}/health"
HEALTH_TIMEOUT_SECONDS = 2
WORKER_START_SECONDS = 120
POLL_SECONDS = 1
ENV_DEFAULTS = {
    "AERONA_IMAGE_WORKER_URL": NATIVE_WORKER_URL,
    "AERONA_IMAGE_WORKER_BACKEND": "mlx",
    "AERONA_MEDIA_BACKEND": "file",
}


def apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def read_env() -> list[str]:
    return ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []


def env_value(lines: list[str], key: str) -> str:
    for line in lines:
        name, _, value = line.partition("=")
        if name.strip() == key:
            return value.strip()
    return ""


def write_env(lines: list[str], key: str, value: str) -> list[str]:
    updated = False
    result: list[str] = []
    for line in lines:
        name, _, _ = line.partition("=")
        if name.strip() == key:
            result.append(f"{key}={value}")
            updated = True
        else:
            result.append(line)
    if not updated:
        result.append(f"{key}={value}")
    return result


def save_env(lines: list[str]) -> None:
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_FILE.chmod(0o600)


def init_env() -> None:
    lines = read_env() or ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    for key, value in ENV_DEFAULTS.items():
        if not env_value(lines, key):
            lines = write_env(lines, key, value)
    if not env_value(lines, SECRET_KEY):
        lines = write_env(lines, SECRET_KEY, secrets.token_urlsafe(SECRET_BYTES))
    save_env(lines)
    print(f".env ready at {ENV_FILE}. Connect a model under Workspace settings, Providers, after the first sign-in.")


def worker_healthy() -> bool:
    try:
        with urllib.request.urlopen(WORKER_HEALTH, timeout=HEALTH_TIMEOUT_SECONDS) as response:
            return bool(response.status == 200)
    except (urllib.error.URLError, OSError):
        return False


def worker_pid() -> int | None:
    if not WORKER_PID.exists():
        return None
    pid = int(WORKER_PID.read_text(encoding="utf-8").strip() or 0)
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        WORKER_PID.unlink(missing_ok=True)
        return None
    return pid


def start_worker() -> None:
    if not apple_silicon():
        sys.exit("The native MLX worker needs Apple Silicon; use `make up` for the GPU container.")
    if worker_healthy():
        print("The image worker is already running.")
        return
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    environment = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    environment["AERONA_IMAGE_WORKER_BACKEND"] = "mlx"
    with WORKER_LOG.open("ab") as log:
        process = subprocess.Popen(
            ["uv", "run", "--extra", "mlx", "aerona-image-worker"],
            cwd=WORKER_DIR,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    WORKER_PID.write_text(str(process.pid), encoding="utf-8")
    deadline = time.monotonic() + WORKER_START_SECONDS
    while time.monotonic() < deadline:
        if worker_healthy():
            print(f"Image worker running on {NATIVE_WORKER_URL} (log: {WORKER_LOG})")
            return
        if process.poll() is not None:
            sys.exit(f"The image worker stopped; see {WORKER_LOG}")
        time.sleep(POLL_SECONDS)
    sys.exit(f"The image worker did not become healthy; see {WORKER_LOG}")


def stop_worker() -> None:
    pid = worker_pid()
    if pid is None:
        print("The image worker is not running from this repository.")
        return
    os.killpg(pid, signal.SIGTERM)
    WORKER_PID.unlink(missing_ok=True)
    print("Image worker stopped.")


def worker_status() -> None:
    state = "healthy" if worker_healthy() else "not reachable"
    print(f"Image worker at {NATIVE_WORKER_URL}: {state}")


def compose(args: list[str], worker_url: str) -> None:
    environment = {**os.environ, "AERONA_DOCKER_IMAGE_WORKER_URL": worker_url}
    subprocess.run(["docker", "compose", *args], cwd=ROOT, env=environment, check=True)


def nvidia_gpu() -> bool:
    return shutil.which("nvidia-smi") is not None


def up() -> None:
    init_env()
    if apple_silicon():
        start_worker()
        compose(["up", "-d", "--build"], f"{DOCKER_HOST_WORKER_URL},{DOCKER_WORKER_URL}")
    elif nvidia_gpu():
        compose(["-f", "docker-compose.yml", "-f", "docker-compose.gpu.yml", "up", "-d", "--build"], DOCKER_WORKER_URL)
    else:
        compose(["up", "-d", "--build"], DOCKER_WORKER_URL)
    print("Weavers of the Void is up: http://127.0.0.1:8080")


def down() -> None:
    compose(["--profile", "media-console", "down"], DOCKER_WORKER_URL)
    if apple_silicon():
        stop_worker()


COMMANDS = {
    "env": init_env,
    "worker-start": start_worker,
    "worker-stop": stop_worker,
    "worker-status": worker_status,
    "up": up,
    "down": down,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up and run the whole Weavers of the Void stack.")
    parser.add_argument("command", choices=sorted(COMMANDS))
    COMMANDS[parser.parse_args().command]()


if __name__ == "__main__":
    main()
