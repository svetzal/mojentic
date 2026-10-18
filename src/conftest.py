"""All library verification stays inside the process."""

import pytest

from scripts.inprocess_http import offline


@pytest.fixture(autouse=True)
def no_network():
    with offline():
        yield
