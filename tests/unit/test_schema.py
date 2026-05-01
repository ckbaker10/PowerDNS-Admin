"""Unit tests for the marshmallow-based ``powerdnsadmin.lib.schema`` port.

The schema module was migrated from the unmaintained ``lima`` library
to marshmallow 3.x in this branch. These tests pin the public dump
contract so we don't accidentally drop or rename a field on a future
upgrade.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "powerdnsadmin" / "lib" / "schema.py"
_spec = importlib.util.spec_from_file_location("pda_schema_under_test", SCHEMA_PATH)
schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schema)


def _domain(id_, name):
    return SimpleNamespace(id=id_, name=name)


def _role(id_, name):
    return SimpleNamespace(id=id_, name=name)


class TestDomainSchema:
    def test_dump_returns_id_and_name(self):
        out = schema.DomainSchema().dump(_domain(1, "example.com"))
        assert out == {"id": 1, "name": "example.com"}

    def test_many_returns_list(self):
        out = schema.DomainSchema(many=True).dump(
            [_domain(1, "a.example"), _domain(2, "b.example")]
        )
        assert isinstance(out, list)
        assert out[0]["name"] == "a.example"
        assert out[1]["id"] == 2


class TestRoleSchema:
    def test_basic_dump(self):
        assert schema.RoleSchema().dump(_role(1, "Administrator")) == {
            "id": 1,
            "name": "Administrator",
        }


class TestApiKeySchema:
    def test_nested_role_and_collections(self):
        key = SimpleNamespace(
            id=42,
            description="ci key",
            key="hashed-secret",
            role=_role(1, "Operator"),
            domains=[_domain(10, "x.example")],
            accounts=[
                SimpleNamespace(id=7, name="acct", domains=[_domain(11, "y.example")]),
            ],
        )
        out = schema.ApiKeySchema().dump(key)
        assert out["id"] == 42
        assert out["description"] == "ci key"
        assert out["key"] == "hashed-secret"
        assert out["role"] == {"id": 1, "name": "Operator"}
        assert out["domains"] == [{"id": 10, "name": "x.example"}]
        assert out["accounts"][0]["name"] == "acct"
        # Nested account -> nested domains list still present.
        assert out["accounts"][0]["domains"] == [{"id": 11, "name": "y.example"}]


class TestApiPlainKeySchema:
    def test_emits_plain_key_not_key(self):
        key = SimpleNamespace(
            id=99,
            description="seeded",
            plain_key="cleartext-shown-once",
            role=_role(2, "User"),
            domains=[],
            accounts=[],
        )
        out = schema.ApiPlainKeySchema().dump(key)
        assert out["plain_key"] == "cleartext-shown-once"
        # The secret-leaking ``key`` field must NOT appear here.
        assert "key" not in out


class TestUserSchema:
    def test_includes_role(self):
        user = SimpleNamespace(
            id=3,
            username="alice",
            firstname="Alice",
            lastname="A",
            email="alice@example.com",
            role=_role(1, "Administrator"),
        )
        out = schema.UserSchema().dump(user)
        assert out["username"] == "alice"
        assert out["role"]["name"] == "Administrator"
