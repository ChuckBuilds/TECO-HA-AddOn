"""
Login backoff: a rejected login must not be retried every poll, or TECO flags the
IP/account as a bot. No network, no browser. Run:

    python tests/test_login_backoff.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sidecar"))
os.environ["CACHE_DIR"] = tempfile.mkdtemp(prefix="teco-backofftest-")
os.environ["TECO_USER"], os.environ["TECO_PASS"] = "u", "p"

import teco_auth_sidecar as T  # noqa: E402


def test_backoff_doubles_and_caps():
    s = T.TecoSession()
    seen = []
    for _ in range(7):
        s._note_login_failure()
        seen.append(s._login_backoff / 60)
    assert seen == [30, 60, 120, 240, 480, 720, 720], seen


def test_paused_login_never_opens_browser():
    s = T.TecoSession()
    s._note_login_failure()
    try:
        asyncio.run(s._login())
    except RuntimeError as e:
        assert "paused" in str(e), e
    else:
        raise AssertionError("login should be paused")
    assert s._browser is None


if __name__ == "__main__":
    test_backoff_doubles_and_caps()
    test_paused_login_never_opens_browser()
    print("ok")
