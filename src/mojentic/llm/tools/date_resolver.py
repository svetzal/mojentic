from typing import Optional

from parsedatetime import Calendar
from pytz import timezone


def resolve_date(relative_date_found: str, reference_date_in_iso8601: Optional[str] = None) -> dict[str, str]:
    cal = Calendar()

    if reference_date_in_iso8601:
        reference_date, _ = cal.parseDT(reference_date_in_iso8601)
    else:
        reference_date = None

    resolved_date, parse_status = cal.parseDT(datetimeString=relative_date_found, sourceTime=reference_date,
                                              tzinfo=timezone("America/Toronto"))

    return {
        "relative_date": relative_date_found,
        "resolved_date": resolved_date.strftime('%Y-%m-%d')
    }


resolve_date_tool = {
    "descriptor": {
        "type": "function",
        "function": {
            "name": "resolve_date",
            "description": "Convert text that specifies a relative date, and convert it to an absolute date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_date_found": {
                        "type": "string",
                        "description": "The text referencing to a relative date."
                    },
                    "reference_date_in_iso8601": {
                        "type": "string",
                        "description": "The date from which the resolved date should be calculated. If not provided, the current date is used."
                    }
                },
                "required": ["relevant_date_found"]
            },
        },
    },
    "python_function": resolve_date,
}
