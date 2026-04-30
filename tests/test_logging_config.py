"""CI guard cho PR2 — structured logging helper.

Scope:

* ``VIBECODE_LOG_LEVEL`` env được honour (DEBUG / INFO / WARNING).
* ``VIBECODE_LOG_JSON=1`` xuất JSON parseable cho mỗi record.
* ``logger.propagate`` = False (tránh bão log khi downstream cấu hình
  root logger).
* Logger được cache per-name — cùng ``name`` trả cùng instance.
* Smoke: ``permission_engine.decide`` emit event khi deny pattern
  (kiểm tra integration giữa helper + module consumer).

Không verify nội dung chi tiết của message (tránh drift khi wording
thay đổi); chỉ verify shape + env wiring.
"""
from __future__ import annotations

import io
import json
import logging
import os
from typing import Iterator

import pytest


# Import helper lazily để mỗi test có thể reset env trước khi get_logger.


@pytest.fixture
def clean_logger_cache() -> Iterator[None]:
    """Reset logger cache + env sandbox cho test độc lập."""
    from vibecodekit import _logging as vl

    saved_env = {
        "VIBECODE_LOG_LEVEL": os.environ.pop("VIBECODE_LOG_LEVEL", None),
        "VIBECODE_LOG_JSON": os.environ.pop("VIBECODE_LOG_JSON", None),
    }
    vl.reset_for_tests()
    try:
        yield
    finally:
        vl.reset_for_tests()
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _make_logger_with_stream(
    name: str, stream: io.StringIO
) -> logging.Logger:
    """Create logger via helper rồi redirect handler sang stream."""
    from vibecodekit._logging import get_logger

    logger = get_logger(name)
    # Replace existing handler(s) với StringIO để capture.
    for h in list(logger.handlers):
        logger.removeHandler(h)
    import logging as _logging
    h = _logging.StreamHandler(stream)
    # Giữ formatter hiện tại theo env — re-instantiate để same class.
    from vibecodekit._logging import _JsonFormatter

    if os.environ.get("VIBECODE_LOG_JSON") == "1":
        h.setFormatter(_JsonFormatter())
    else:
        h.setFormatter(
            _logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
    logger.addHandler(h)
    return logger


def test_logger_respects_log_level(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_LEVEL"] = "WARNING"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_level", stream)
    logger.info("info message")
    logger.warning("warn message")
    output = stream.getvalue()
    assert "warn message" in output
    assert "info message" not in output


def test_logger_debug_level_passes_through(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_LEVEL"] = "DEBUG"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_debug", stream)
    logger.debug("debug message")
    assert "debug message" in stream.getvalue()


def test_invalid_level_falls_back_to_info(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_LEVEL"] = "NOT_A_LEVEL"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_invalid", stream)
    logger.info("info msg")
    logger.debug("debug msg")
    output = stream.getvalue()
    assert "info msg" in output
    assert "debug msg" not in output


def test_json_format(clean_logger_cache: None) -> None:
    os.environ["VIBECODE_LOG_JSON"] = "1"
    os.environ["VIBECODE_LOG_LEVEL"] = "INFO"
    stream = io.StringIO()
    logger = _make_logger_with_stream("vibecodekit._test_json", stream)
    logger.info("hello", extra={"decision": "deny", "rule_id": "R-001"})
    raw = stream.getvalue().strip().splitlines()[-1]
    payload = json.loads(raw)
    assert payload["level"] == "INFO"
    assert payload["msg"] == "hello"
    assert payload["name"] == "vibecodekit._test_json"
    assert payload["decision"] == "deny"
    assert payload["rule_id"] == "R-001"
    assert "ts" in payload


def test_logger_does_not_propagate(clean_logger_cache: None) -> None:
    from vibecodekit._logging import get_logger

    logger = get_logger("vibecodekit._test_propagate")
    assert logger.propagate is False


def test_logger_is_cached_per_name(clean_logger_cache: None) -> None:
    from vibecodekit._logging import get_logger

    a = get_logger("vibecodekit._test_cache")
    b = get_logger("vibecodekit._test_cache")
    assert a is b
    # Handler chỉ được add một lần dù gọi nhiều lần.
    assert len([h for h in a.handlers]) == 1


def test_permission_engine_logs_deny(clean_logger_cache: None) -> None:
    """Integration smoke: permission_engine phải emit event khi deny."""
    os.environ["VIBECODE_LOG_LEVEL"] = "DEBUG"
    os.environ["VIBECODE_LOG_JSON"] = "1"
    stream = io.StringIO()
    _make_logger_with_stream("vibecodekit.permission_engine", stream)

    from vibecodekit.permission_engine import decide

    decision = decide("rm -rf /", mode="default")
    assert decision["decision"] == "deny"
    logged = stream.getvalue().strip()
    assert logged, "expected at least one log line for deny decision"
    last = json.loads(logged.splitlines()[-1])
    assert last["decision"] == "deny"
    assert last["name"] == "vibecodekit.permission_engine"
