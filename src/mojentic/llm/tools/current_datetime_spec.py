import os
import time
from datetime import UTC, datetime

import pytest

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

    def should_format_local_offset_and_name_from_the_returned_instant(
        self, local_timezone
    ):
        result = CurrentDateTimeTool().run("%Y-%m-%d %H:%M:%S %z %Z")
        expected = datetime.fromtimestamp(result["timestamp"], tz=UTC).astimezone()

        assert result["current_datetime"] == expected.strftime(
            "%Y-%m-%d %H:%M:%S %z %Z"
        )
        assert result["timezone"] == expected.tzname()

    def should_preserve_default_local_wall_clock_format(self, local_timezone):
        result = CurrentDateTimeTool().run()
        expected = datetime.fromtimestamp(result["timestamp"], tz=UTC).astimezone()

        assert result["current_datetime"] == expected.strftime("%Y-%m-%d %H:%M:%S")
