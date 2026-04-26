"""Shared fixtures for integration tests.

The ``client`` fixture is session-scoped because the app is stateless by design
(ADR-001 guarantees no engine state, ADR-002 ensures every response is built
from scratch); reusing one ``TestClient`` across the suite cuts a few hundred
milliseconds off the run and keeps the determinism test cheap.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Yield a TestClient with lifespan startup/shutdown wrapped."""
    with TestClient(app) as c:
        yield c
