"""
Auth regression tests for the sidecar API. No network, no TECO credentials.

These exist because of a real bug: `_auth` exempted any request carrying an
`X-Ingress-Path` header, on the assumption that only Home Assistant ingress would
send one. Headers are attacker-controlled, so ANY client could send it and read
the entire billing archive -- with a token configured and the port published to
the LAN, that is the whole archive readable by anyone on the network.

Ingress is now proven by the request's SOURCE ADDRESS (the Supervisor network),
not by a header. Run:

    python tests/test_auth.py
"""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sidecar"))

TOKEN = "unit-test-token"
os.environ["SIDECAR_TOKEN"] = TOKEN
os.environ["CACHE_DIR"] = tempfile.mkdtemp(prefix="teco-authtest-")

import teco_auth_sidecar as T  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

T.app.router.lifespan_context = None       # never start the poll loop
PROTECTED = ("/bills", "/export", "/data")
INGRESS_HDR = {"X-Ingress-Path": "/api/hassio_ingress/abcdef"}

failures: list[str] = []


def check(label: str, got: int, want: int) -> None:
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label:56} -> {got} (want {want})")
    if not ok:
        failures.append(label)


def main() -> int:
    lan = TestClient(T.app, raise_server_exceptions=False)
    # a request that genuinely came through Supervisor ingress
    ingress = TestClient(T.app, client=("172.30.32.2", 5000),
                         raise_server_exceptions=False)

    print("token configured -- protected endpoints require it")
    for path in PROTECTED:
        if path == "/data":
            continue                        # would hit TECO; covered by /bills+/export
        check(f"{path} no token", lan.get(path).status_code, 401)
        check(f"{path} wrong token",
              lan.get(path, headers={"X-Auth-Token": "wrong"}).status_code, 401)
        check(f"{path} correct token",
              lan.get(path, headers={"X-Auth-Token": TOKEN}).status_code, 200)

        # the bug: a forged header must NOT be accepted from an off-network client
        check(f"{path} forged X-Ingress-Path from LAN",
              lan.get(path, headers=INGRESS_HDR).status_code, 401)
        check(f"{path} forged header + wrong token from LAN",
              lan.get(path, headers={**INGRESS_HDR,
                                     "X-Auth-Token": "wrong"}).status_code, 401)

        # genuine ingress still works, and the header is still required
        check(f"{path} real ingress (supervisor IP + header)",
              ingress.get(path, headers=INGRESS_HDR).status_code, 200)
        check(f"{path} supervisor IP but no ingress header",
              ingress.get(path).status_code, 401)

    # a spoofed forwarding header must not launder the client address either
    check("/bills X-Forwarded-For: 172.30.32.2 (spoofed)",
          lan.get("/bills", headers={**INGRESS_HDR,
                                     "X-Forwarded-For": "172.30.32.2"}).status_code, 401)

    # /reassemble triggers live TECO fetches -- it must be gated too
    check("/reassemble forged header from LAN",
          lan.post("/reassemble", params={"invoice_id": "1"},
                   headers=INGRESS_HDR).status_code, 401)

    # /health is intentionally open (no billing data) but must not leak the token
    r = lan.get("/health")
    check("/health reachable without a token", r.status_code, 200)
    check("/health does not leak the token", 0 if TOKEN in r.text else 1, 1)

    print()
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        return 1
    print("all auth checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
