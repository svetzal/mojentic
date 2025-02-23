import pytest

from mojentic.llm.tools.date_resolver import ResolveDateTool


@pytest.fixture
def date_resolver():
    return ResolveDateTool()


class DescribeResolveDateTool:

    def should_resolve_date_without_reference(self, date_resolver):
        """
        Given a date resolver
        When resolving "next Friday" without a reference date provided
        Then it should return some resolved date (which will change whenever this test is run)
        """
        result = date_resolver.run(relative_date_found="next Friday")
        assert result["relative_date"] == "next Friday"
        assert "resolved_date" in result


    def should_resolve_date_with_reference(self, date_resolver):
        """
        Given a date resolver
        When resolving "next Friday" with a reference date of 2023-10-01
        Then it should return 2023-10-06
        """
        reference_date = "2023-10-01"
        result = date_resolver.run(relative_date_found="next Friday", reference_date_in_iso8601=reference_date)
        assert result["relative_date"] == "next Friday"
        assert result["resolved_date"] == "2023-10-06"  # Adjust the expected date based on the reference date
