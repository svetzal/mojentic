from mojentic.llm.tools.date_resolver import resolve_date, DateResolverTool


def test_resolve_date_without_reference():
    result = resolve_date(relative_date_found="next Friday")
    assert result["relative_date"] == "next Friday"
    assert "resolved_date" in result


def test_resolve_date_with_reference():
    reference_date = "2023-10-01"
    result = resolve_date(relative_date_found="next Friday", reference_date_in_iso8601=reference_date)
    assert result["relative_date"] == "next Friday"
    assert result["resolved_date"] == "2023-10-06"  # Adjust the expected date based on the reference date
