"""Conformance runner — validates attago-spec fixtures against a live API.

Usage:
    ATTAGO_BASE_URL=https://dev.attago.bid \\
    ATTAGO_API_KEY=ak_live_... \\
    pytest tests/conformance/ -v -m conformance

Loads fixtures from the attago-spec repo (cloned by CI or local),
sends real HTTP requests, and validates response status + required fields.
"""

import json
import os
from pathlib import Path

import httpx
import pytest

SPEC_DIR = os.environ.get("ATTAGO_SPEC_DIR", str(Path(__file__).parents[2] / "attago-spec"))
FIXTURE_DIR = Path(SPEC_DIR) / "spec" / "fixtures" / "rest"
BASE_URL = os.environ.get("ATTAGO_BASE_URL", "")
API_KEY = os.environ.get("ATTAGO_API_KEY", "")

SKIP_FIXTURES = {"user-profile-success.json", "user-profile-unauthorized.json"}


def load_fixtures():
    """Load all REST fixture JSON files from attago-spec."""
    if not FIXTURE_DIR.exists():
        return []
    fixtures = []
    for f in sorted(FIXTURE_DIR.iterdir()):
        if not f.suffix == ".json" or f.name in SKIP_FIXTURES:
            continue
        data = json.loads(f.read_text())
        needs_auth = data.get("request", {}).get("headers", {}).get("Authorization")
        if needs_auth and not API_KEY:
            continue
        fixtures.append(pytest.param(data, id=f.stem))
    return fixtures


@pytest.mark.conformance
@pytest.mark.skipif(not BASE_URL, reason="ATTAGO_BASE_URL not set")
@pytest.mark.skipif(not FIXTURE_DIR.exists(), reason=f"Fixture dir not found: {FIXTURE_DIR}")
class TestConformance:
    @pytest.mark.parametrize("fixture", load_fixtures())
    def test_fixture(self, fixture):
        req = fixture["request"]
        expected = fixture["response"]

        # Build URL
        url = BASE_URL.rstrip("/") + req["path"]
        params = req.get("query", {})

        # Build headers
        headers = {"Accept": "application/json", **req.get("headers", {})}
        if headers.get("X-API-Key") and API_KEY:
            headers["X-API-Key"] = API_KEY

        # Build body
        content = None
        if req.get("body"):
            content = json.dumps(req["body"]).encode()
            headers["Content-Type"] = "application/json"

        # Send
        resp = httpx.request(
            method=req["method"],
            url=url,
            headers=headers,
            params=params,
            content=content,
            timeout=30.0,
        )

        # Validate status
        assert resp.status_code == expected["status"], (
            f"Expected {expected['status']}, got {resp.status_code}"
        )
