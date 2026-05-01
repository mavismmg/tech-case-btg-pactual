import json
import logging

from app.core.logging import JsonFormatter


def test_json_formatter_outputs_parseable_json_with_extra_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Operation completed",
        args=(),
        exc_info=None,
    )
    record.operation = "test_operation"
    record.user_id = 42

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "Operation completed"
    assert payload["operation"] == "test_operation"
    assert payload["user_id"] == 42
    assert "timestamp" in payload


def test_json_formatter_redacts_sensitive_extra_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Sensitive operation",
        args=(),
        exc_info=None,
    )
    record.password = "secret"

    payload = json.loads(formatter.format(record))

    assert payload["password"] == "[REDACTED]"


def test_json_formatter_can_pretty_print_json():
    formatter = JsonFormatter(pretty=True)
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Pretty operation",
        args=(),
        exc_info=None,
    )
    record.operation = "pretty_operation"

    formatted = formatter.format(record)
    payload = json.loads(formatted)

    assert "\n" in formatted
    assert '  "operation": "pretty_operation"' in formatted
    assert payload["operation"] == "pretty_operation"
