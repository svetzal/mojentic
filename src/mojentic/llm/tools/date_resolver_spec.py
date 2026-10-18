import time

import pytest

from mojentic.llm.tools.date_resolver import ResolveDateTool


@pytest.fixture
def date_resolver(monkeypatch):
    original = time.localtime
    fixed = time.struct_time((2023, 10, 1, 12, 0, 0, 6, 274, 0))
    monkeypatch.setattr(
        time,
        "localtime",
        lambda seconds=None: fixed if seconds is None else original(seconds),
    )
    return ResolveDateTool()


class DescribeResolveDateTool:
    def should_resolve_date_without_reference(self, date_resolver):
        result = date_resolver.run(relative_date_found="next Friday")

        assert result == {
            "relative_date": "next Friday",
            "resolved_date": "2023-10-06",
            "summary": "The date on 'next Friday' is 2023-10-06",
        }

    def should_resolve_date_with_reference(self, date_resolver):
        result = date_resolver.run(
            relative_date_found="next Friday", reference_date_in_iso8601="2023-10-01"
        )

        assert result["relative_date"] == "next Friday"
        assert result["resolved_date"] == "2023-10-06"
