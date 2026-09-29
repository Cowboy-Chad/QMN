import asyncio
import os
import subprocess

DEFAULT_MODEL = os.environ.get("FABRIC_MODEL", "deepseek/deepseek-v4-flash")
DEFAULT_VENDOR = os.environ.get("FABRIC_VENDOR", "OpenRouter")
# Overridable so the binary path can be changed without rebuilding the image.
FABRIC_BIN = os.environ.get("FABRIC_BIN", "fabric")
FABRIC_TIMEOUT = int(os.environ.get("FABRIC_TIMEOUT", "600"))
MAX_RETRIES = int(os.environ.get("FABRIC_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.environ.get("FABRIC_RETRY_BASE_DELAY", "2.0"))

# The patterns available for selection.
#
# Derived from the vendored pattern directory rather than hand-maintained, so the
# list the UI advertises and the patterns actually present on disk cannot drift.
# Nothing validates the incoming `pattern` string before it reaches
# `fabric -p` — fabric resolves it from disk — so an entry here that had no
# matching directory would be advertised and then fail at analysis time.
_PATTERNS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fabric_patterns"
)

if os.path.isdir(_PATTERNS_DIR):
    CURATED_PATTERNS = sorted(
        d for d in os.listdir(_PATTERNS_DIR) if os.path.isdir(os.path.join(_PATTERNS_DIR, d))
    )
else:  # pragma: no cover - the directory ships with the repo
    CURATED_PATTERNS = []


async def run_fabric(pattern: str, input_text: str, model: str | None = None, vendor: str | None = None) -> str:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        cmd = [FABRIC_BIN, "-p", pattern]
        cmd.extend(["-m", model or DEFAULT_MODEL])
        if vendor or DEFAULT_VENDOR:
            cmd.extend(["-V", vendor or DEFAULT_VENDOR])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_text.encode()), timeout=FABRIC_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"fabric analysis timed out after {FABRIC_TIMEOUT}s for pattern '{pattern}'")
        if proc.returncode == 0:
            return stdout.decode().strip()

        stderr_str = stderr.decode()
        if proc.returncode == 1 and "429" in stderr_str and attempt < MAX_RETRIES:
            last_error = stderr_str
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            await asyncio.sleep(delay)
            continue

        raise RuntimeError(f"fabric exited code {proc.returncode}: {stderr_str}")

    raise RuntimeError(f"fabric exited code 1 after {MAX_RETRIES} retries: {last_error}")


async def list_patterns() -> list[dict]:
    return [{"name": n, "description": ""} for n in CURATED_PATTERNS]


async def read_pattern(pattern: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        FABRIC_BIN,
        "--readpattern", pattern,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"fabric --readpattern failed: {stderr.decode()}")
    return stdout.decode()