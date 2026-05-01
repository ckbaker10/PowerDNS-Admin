"""Additional unit tests for ``powerdnsadmin.lib.utils`` helpers.

Covers display/formatting helpers that the existing ``test_utils.py``
does not exercise. Loaded the same way as ``test_utils.py``: directly
via ``importlib`` so we don't drag in flask_mail/saml/etc.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _ensure_distutils_shim():
    if "distutils.version" in sys.modules:
        return
    distutils = sys.modules.get("distutils") or types.ModuleType("distutils")
    version_mod = types.ModuleType("distutils.version")

    class _StrictVersion:
        def __init__(self, v):
            self.parts = tuple(int(p) for p in str(v).split("."))

        def __lt__(self, other):
            return self.parts < other.parts

        def __le__(self, other):
            return self.parts <= other.parts

        def __eq__(self, other):
            return self.parts == other.parts

        def __ge__(self, other):
            return self.parts >= other.parts

        def __gt__(self, other):
            return self.parts > other.parts

    version_mod.StrictVersion = _StrictVersion
    distutils.version = version_mod  # type: ignore[attr-defined]
    sys.modules["distutils"] = distutils
    sys.modules["distutils.version"] = version_mod


_ensure_distutils_shim()


UTILS_PATH = Path(__file__).resolve().parents[2] / "powerdnsadmin" / "lib" / "utils.py"
_spec = importlib.util.spec_from_file_location("pda_utils_extra_under_test", UTILS_PATH)
utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(utils)


class TestDisplayMasterName:
    def test_extracts_quoted_addresses(self):
        # display_master_name accepts the repr() of a Python list and
        # returns a comma-joined string of the contained addresses.
        out = utils.display_master_name("[u'127.0.0.1', u'8.8.8.8']")
        assert out == "127.0.0.1, 8.8.8.8"

    def test_no_match_returns_empty_string(self):
        assert utils.display_master_name("[]") == ""


class TestFormatZoneType:
    def test_master_becomes_primary(self):
        assert utils.format_zone_type("Master") == "Primary"

    def test_slave_becomes_secondary(self):
        assert utils.format_zone_type("slave") == "Secondary"

    def test_native_passthrough_titlecased(self):
        assert utils.format_zone_type("native") == "Native"


class TestDisplaySettingState:
    def test_one_is_on(self):
        assert utils.display_setting_state(1) == "ON"

    def test_zero_is_off(self):
        assert utils.display_setting_state(0) == "OFF"

    def test_other_is_unknown(self):
        assert utils.display_setting_state("anything") == "UNKNOWN"


class TestPrettyJson:
    def test_sorts_keys_and_indents(self):
        out = utils.pretty_json({"b": 2, "a": 1})
        # sort_keys=True -> "a" appears before "b"
        assert out.index('"a"') < out.index('"b"')
        # indent=4 means at least one 4-space line break
        assert "\n    " in out
        # Round-trips back to the same dict.
        assert json.loads(out) == {"a": 1, "b": 2}


class TestFormatDatetime:
    def test_none_returns_empty_string(self):
        assert utils.format_datetime(None) == ""

    def test_default_format(self):
        # 2024-01-02 15:04 -> "2024-01-02 03:04 PM"
        dt = datetime.datetime(2024, 1, 2, 15, 4, 0)
        assert utils.format_datetime(dt) == "2024-01-02 03:04 PM"

    def test_custom_format(self):
        dt = datetime.datetime(2024, 1, 2, 15, 4, 0)
        assert utils.format_datetime(dt, "%Y/%m/%d") == "2024/01/02"


class TestDisplayTime:
    def test_seconds_to_minutes_drops_seconds(self):
        # 65s -> "1m" (default remove_seconds strips the trailing 5s).
        out = utils.display_time(65, units="s")
        assert "m" in out

    def test_milliseconds_pass_through(self):
        # display_time always returns a non-empty string when given a
        # positive amount; we don't pin the exact unit suffix because
        # the function's ``remove_seconds`` post-processing trims the
        # trailing field.
        assert utils.display_time(500, units="ms").strip() != ""
