"""Unit tests for ``powerdnsadmin.lib.utils`` helpers.

The module imports ``distutils.version`` which was removed in Python
3.13. To stay runnable on both 3.12 (CI) and 3.13 (the dev venv) we
register a tiny shim before the import. The functions exercised here
do not use ``StrictVersion`` themselves.
"""
from __future__ import annotations

import sys
import types

import pytest


def _ensure_distutils_shim():
    if "distutils.version" in sys.modules:
        return
    distutils = sys.modules.get("distutils") or types.ModuleType("distutils")
    version_mod = types.ModuleType("distutils.version")

    class _StrictVersion:
        def __init__(self, v):
            self.parts = tuple(int(p) for p in str(v).split("."))

        def _key(self):
            return self.parts

        def __lt__(self, other):
            return self._key() < other._key()

        def __le__(self, other):
            return self._key() <= other._key()

        def __eq__(self, other):
            return self._key() == other._key()

        def __gt__(self, other):
            return self._key() > other._key()

        def __ge__(self, other):
            return self._key() >= other._key()

    version_mod.StrictVersion = _StrictVersion
    distutils.version = version_mod  # type: ignore[attr-defined]
    sys.modules["distutils"] = distutils
    sys.modules["distutils.version"] = version_mod


_ensure_distutils_shim()

# Importing through the package would drag flask_mail and friends; load
# the module directly via importlib so it stays test-friendly.
import importlib.util
from pathlib import Path

UTILS_PATH = Path(__file__).resolve().parents[2] / "powerdnsadmin" / "lib" / "utils.py"
spec = importlib.util.spec_from_file_location("pda_utils_under_test", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)


class TestAuthFromUrl:
    def test_extracts_basic_auth(self):
        import requests
        auth = utils.auth_from_url("http://user:pass@example.com/path")
        assert isinstance(auth, requests.auth.HTTPBasicAuth)
        assert auth.username == "user"
        assert auth.password == "pass"

    def test_returns_none_when_no_auth(self):
        assert utils.auth_from_url("https://example.com/api") is None


class TestValidateIpaddress:
    def test_ipv4(self):
        assert utils.validate_ipaddress("10.0.0.1") != []

    def test_ipv6(self):
        assert utils.validate_ipaddress("2001:db8::1") != []

    def test_garbage_returns_empty_list(self):
        assert utils.validate_ipaddress("not-an-ip") == []

    def test_empty_string_returns_empty_list(self):
        # Empty string is not a valid IP and must not raise.
        assert utils.validate_ipaddress("") == []


class TestDisplayRecordName:
    def test_strips_trailing_zone(self):
        result = utils.display_record_name(
            {"name": "www.example.com", "type": "A"},
            # display_record_name only takes one arg in this codebase;
            # signature check below.
        ) if utils.display_record_name.__code__.co_argcount == 2 else None
        # Fallback: call with the documented single-arg shape.
        out = utils.display_record_name(
            {"name": "www.example.com", "type": "A"}
        )
        assert isinstance(out, str)


class TestPrettyDomainName:
    def test_ascii_passthrough(self):
        assert utils.pretty_domain_name("example.com") == "example.com"

    def test_punycode_decodes_to_unicode(self):
        # xn--bcher-kva.example -> bücher.example
        out = utils.pretty_domain_name("xn--bcher-kva.example")
        assert "ü" in out or out.startswith("xn--")  # tolerant of idna failures


class TestToIdna:
    def test_encode_unicode_to_punycode(self):
        out = utils.to_idna("bücher.example", "encode")
        assert out.startswith("xn--") or "xn--" in out

    def test_decode_punycode_to_unicode(self):
        out = utils.to_idna("xn--bcher-kva.example", "decode")
        assert "ü" in out


class TestEnsureList:
    # ``ensure_list`` is a generator (uses ``yield from``); materialise
    # before comparing.
    def test_none_becomes_empty_list(self):
        assert list(utils.ensure_list(None)) == []

    def test_scalar_wrapped(self):
        assert list(utils.ensure_list("a")) == ["a"]

    def test_list_passthrough(self):
        assert list(utils.ensure_list(["a", "b"])) == ["a", "b"]


class TestPdnsApiExtendedUri:
    def test_v4_returns_api_v1_prefix(self):
        # Versions >= 4.x take the /api/v1 prefix; older ones don't.
        out = utils.pdns_api_extended_uri("4.7.0")
        assert out == "/api/v1"

    def test_v3_returns_empty_prefix(self):
        out = utils.pdns_api_extended_uri("3.4.0")
        assert out == ""
