import pytest


@pytest.fixture
def anyio_backend():
    """Restrict anyio tests to asyncio so trio is not required."""
    return "asyncio"
