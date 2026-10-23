"""All library verification stays inside the process."""

import pytest

from scripts.inprocess_http import offline


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path / "empty-tiktoken-cache"))
    with offline():
        yield
