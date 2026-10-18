import os
import time
from datetime import UTC, datetime

import pytest

from mojentic.llm.tools import current_datetime
from mojentic.llm.tools.current_datetime import CurrentDateTimeTool


class DescribeCurrentDateTimeTool:
    @pytest.fixture
    def local_timezone(self):
        previous = os.environ.get("TZ")
        os.environ["TZ"] = "EST5EDT,M3.2.0,M11.1.0"
        time.tzset()
        yield
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()

    @pytest.fixture(params=[(1, "-0500 EST"), (7, "-0400 EDT")])
    def instant(self, request, monkeypatch):
        month, offset = request.param
        instant = datetime(2026, month, 15, 12, 30, 45, tzinfo=UTC)

        class FixedClock:
            @staticmethod
            def now(tz):
                return instant.astimezone(tz)

        monkeypatch.setattr(current_datetime, "datetime", FixedClock)
        return instant, offset

    def should_format_local_offset_and_name_from_the_returned_instant(
        self, local_timezone, instant
    ):
        fixed, offset = instant

        result = CurrentDateTimeTool().run("%Y-%m-%d %H:%M:%S %z %Z")

        assert (
            result["current_datetime"]
            == fixed.astimezone().strftime("%Y-%m-%d %H:%M:%S") + " " + offset
        )
        assert result["timestamp"] == fixed.timestamp()
        assert result["timezone"] == offset.split()[1]

    def should_preserve_default_local_wall_clock_format(self, local_timezone, instant):
        fixed, _ = instant

        result = CurrentDateTimeTool().run()

        assert result["current_datetime"] == fixed.astimezone().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        assert result["timestamp"] == fixed.timestamp()
