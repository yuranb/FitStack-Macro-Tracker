"""E2E fixtures: a local PostgREST stub plus a real `streamlit run` process.

The app is pointed at the stub via the SUPABASE_URL/SUPABASE_KEY env override
(see src/app.py::_supabase_config), so no secrets.toml and no network access
are involved. Playwright drives a real browser against the served UI.
"""

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from postgrest_stub import StubServer

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STREAMLIT_PORT = 8931
STREAMLIT_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"

# local browser installs go into the repo (see DECISIONS.md); CI uses the
# default cache location, so only set this when the folder exists
_LOCAL_BROWSERS = REPO_ROOT / ".playwright-browsers"
if _LOCAL_BROWSERS.exists():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(_LOCAL_BROWSERS))


@pytest.fixture(scope="session")
def stub_server():
    server = StubServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def fresh_stub_data(stub_server):
    """Reset the stub's in-memory tables so every test starts empty."""
    stub_server.state.reset()
    return stub_server


@pytest.fixture(scope="session")
def streamlit_app(stub_server):
    """Launch `streamlit run src/app.py` wired to the stub, wait for it."""
    env = dict(os.environ)
    env.update(
        SUPABASE_URL=stub_server.base_url,
        SUPABASE_KEY="e2e-test-key",
        STREAMLIT_BROWSER_GATHER_USAGE_STATS="false",
    )
    process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "src/app.py",
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={STREAMLIT_PORT}",
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_http(STREAMLIT_URL, timeout=60)
        yield STREAMLIT_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _wait_for_http(url, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    raise RuntimeError(f"Streamlit did not become reachable at {url}")
