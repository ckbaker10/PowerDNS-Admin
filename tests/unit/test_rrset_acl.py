"""Unit tests for the pure-function rrset_acl evaluator.

These tests do not import any Flask/SQLAlchemy machinery - the helper
under test is intentionally framework-free so it can be exercised
without spinning up the application.
"""
import importlib.util
import pathlib
import sys

import pytest

# Load the module directly so we don't trigger powerdnsadmin/__init__.py
# (which pulls in Flask). The helper has no Flask deps of its own.
_HELPER_PATH = (pathlib.Path(__file__).resolve().parents[2]
                / "powerdnsadmin" / "lib" / "rrset_acl.py")
_spec = importlib.util.spec_from_file_location("rrset_acl_under_test",
                                               _HELPER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["rrset_acl_under_test"] = _mod
_spec.loader.exec_module(_mod)

AclRule = _mod.AclRule
evaluate_patch = _mod.evaluate_patch
match_pattern = _mod.match_pattern
pattern_within_zone = _mod.pattern_within_zone
validate_pattern_syntax = _mod.validate_pattern_syntax


# ----- match_pattern -------------------------------------------------

@pytest.mark.parametrize("pattern,name,expected", [
    ("_acme-challenge.example.com.", "_acme-challenge.example.com.", True),
    ("_acme-challenge.example.com",  "_acme-challenge.example.com.", True),
    ("_acme-challenge.example.com.", "_ACME-CHALLENGE.EXAMPLE.COM",  True),
    ("_acme-challenge.example.com.", "_acme-challenge.other.com.",   False),
    ("_acme-challenge.*.example.com.",
        "_acme-challenge.host.example.com.", True),
    ("_acme-challenge.*.example.com.",
        "_acme-challenge.a.b.example.com.", False),
    ("_acme-challenge.*.example.com.",
        "_acme-challenge.example.com.", False),
    ("foo*.example.com.", "foobar.example.com.", False),  # partial wildcard
])
def test_match_pattern(pattern, name, expected):
    assert match_pattern(pattern, name) is expected


# ----- validate_pattern_syntax --------------------------------------

@pytest.mark.parametrize("pattern,ok", [
    ("_acme-challenge.example.com.", True),
    ("_acme-challenge.*.example.com.", True),
    ("",                                False),
    ("foo*.example.com.",               False),
    ("*.*.example.com.",                False),
    ("invalid_chars!.example.com.",     False),
])
def test_validate_pattern_syntax(pattern, ok):
    got, _ = validate_pattern_syntax(pattern)
    assert got is ok


def test_pattern_within_zone():
    assert pattern_within_zone("_acme-challenge.example.com.", "example.com")
    assert pattern_within_zone("example.com.", "example.com")
    assert not pattern_within_zone("other.com.", "example.com")


# ----- evaluate_patch -----------------------------------------------

def _rule(name="_acme-challenge.host.example.com.", **kw):
    return AclRule(domain_name="example.com",
                   record_name_pattern=name,
                   record_type=kw.get("record_type", "TXT"),
                   allow_replace=kw.get("allow_replace", True),
                   allow_delete=kw.get("allow_delete", True))


def _patch(name="_acme-challenge.host.example.com.",
           type_="TXT", changetype="REPLACE"):
    return {"rrsets": [{"name": name, "type": type_,
                        "changetype": changetype,
                        "ttl": 60, "records": [{"content": "\"x\""}]}]}


def test_evaluate_patch_allows_matching_rrset():
    ok, reason = evaluate_patch([_rule()], "example.com.", _patch())
    assert ok, reason


def test_evaluate_patch_denies_wrong_name():
    ok, reason = evaluate_patch(
        [_rule()], "example.com.",
        _patch(name="_acme-challenge.evil.example.com."))
    assert not ok
    assert "not permitted" in reason


def test_evaluate_patch_denies_wrong_type():
    ok, _ = evaluate_patch(
        [_rule()], "example.com.", _patch(type_="A"))
    assert not ok


def test_evaluate_patch_denies_wrong_zone():
    ok, _ = evaluate_patch(
        [_rule()], "other.com.", _patch())
    assert not ok


def test_evaluate_patch_denies_unknown_changetype():
    ok, _ = evaluate_patch([_rule()], "example.com.",
                            _patch(changetype="UNKNOWN"))
    assert not ok


def test_evaluate_patch_denies_delete_when_disallowed():
    rule = _rule(allow_delete=False)
    ok, _ = evaluate_patch([rule], "example.com.",
                            _patch(changetype="DELETE"))
    assert not ok


def test_evaluate_patch_atomic_rejects_mixed_batch():
    body = {"rrsets": [
        {"name": "_acme-challenge.host.example.com.", "type": "TXT",
         "changetype": "REPLACE", "ttl": 60, "records": []},
        {"name": "_acme-challenge.evil.example.com.", "type": "TXT",
         "changetype": "REPLACE", "ttl": 60, "records": []},
    ]}
    ok, _ = evaluate_patch([_rule()], "example.com.", body)
    assert not ok


def test_evaluate_patch_empty_body_denied():
    ok, _ = evaluate_patch([_rule()], "example.com.", {})
    assert not ok
    ok, _ = evaluate_patch([_rule()], "example.com.", {"rrsets": []})
    assert not ok


def test_evaluate_patch_wildcard_rule():
    rule = _rule(name="_acme-challenge.*.example.com.")
    ok, _ = evaluate_patch(
        [rule], "example.com.",
        _patch(name="_acme-challenge.host.example.com."))
    assert ok
    ok, _ = evaluate_patch(
        [rule], "example.com.",
        _patch(name="_acme-challenge.a.b.example.com."))
    assert not ok
