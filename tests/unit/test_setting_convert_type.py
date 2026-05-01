"""Unit tests for ``AppSettings.convert_type`` in ``lib/settings.py``.

The static ``convert_type`` is used by every ``Setting().get()`` call
to coerce DB-stored strings into Python types; bugs here have a wide
blast radius. ``lib/settings.py`` only depends on ``os`` and
``pathlib`` so it loads cleanly under pytest with no Flask/DB context.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SETTINGS_PATH = (
    Path(__file__).resolve().parents[2]
    / "powerdnsadmin"
    / "lib"
    / "settings.py"
)
_spec = importlib.util.spec_from_file_location("pda_app_settings_under_test", SETTINGS_PATH)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)
AppSettings = mod.AppSettings


# Pick representative names from each declared type for parametrisation.
def _name_of_type(t):
    for name, decl_type in AppSettings.types.items():
        if decl_type is t:
            return name
    raise AssertionError("no setting declared with type {0!r}".format(t))


BOOL_NAME = _name_of_type(bool)
INT_NAME = _name_of_type(int)
STR_NAME = _name_of_type(str)
DICT_NAME = _name_of_type(dict)
LIST_NAME = _name_of_type(list)


class TestBool:
    @pytest.mark.parametrize("raw", ["True", "true", "1"])
    def test_truthy_strings(self, raw):
        assert AppSettings.convert_type(BOOL_NAME, raw) is True

    @pytest.mark.parametrize("raw", ["False", "false", "0", "", "no"])
    def test_falsy_strings(self, raw):
        assert AppSettings.convert_type(BOOL_NAME, raw) is False


class TestInt:
    def test_string_to_int(self):
        assert AppSettings.convert_type(INT_NAME, "42") == 42

    def test_int_passthrough(self):
        assert AppSettings.convert_type(INT_NAME, 7) == 7

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            AppSettings.convert_type(INT_NAME, "not-a-number")


class TestFloatExplicit:
    def test_explicit_float_setting(self, monkeypatch):
        # No production setting is declared as ``float``; pin the
        # behaviour anyway by injecting a temporary entry.
        monkeypatch.setitem(AppSettings.types, "_unit_test_float", float)
        assert AppSettings.convert_type("_unit_test_float", "1.5") == 1.5


class TestStr:
    def test_int_coerced_to_string(self):
        assert AppSettings.convert_type(STR_NAME, 123) == "123"


class TestDictAndList:
    def test_json_dict(self):
        assert AppSettings.convert_type(DICT_NAME, '{"A": true}') == {"A": True}

    def test_legacy_python_repr_dict(self):
        # Backwards compat: lima/older versions stored single-quoted
        # ``True``/``False`` Python repr literals; convert_type fixes
        # them up before json.loads.
        assert AppSettings.convert_type(DICT_NAME, "{'A': True}") == {"A": True}

    def test_unparseable_raises_value_error(self):
        with pytest.raises(ValueError):
            AppSettings.convert_type(DICT_NAME, "{not-json-at-all")

    def test_json_list(self):
        assert AppSettings.convert_type(LIST_NAME, '["a", "b"]') == ["a", "b"]


class TestUnknownName:
    def test_passes_value_through_unchanged(self):
        sentinel = object()
        assert AppSettings.convert_type("definitely-not-a-real-setting", sentinel) is sentinel
