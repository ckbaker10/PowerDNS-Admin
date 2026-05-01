"""Unit tests for ``powerdnsadmin.services.token``.

The module is a thin wrapper around itsdangerous; we exercise the
round-trip plus expiry behaviour with a minimal Flask app context so
no DB, model imports or distutils shim are required.
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest
from flask import Flask
from itsdangerous import URLSafeTimedSerializer


TOKEN_PATH = Path(__file__).resolve().parents[2] / "powerdnsadmin" / "services" / "token.py"
_spec = importlib.util.spec_from_file_location("pda_token_under_test", TOKEN_PATH)
token_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(token_mod)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "unit-test-secret-key"
    app.config["SALT"] = "unit-test-salt"
    return app


class TestRoundTrip:
    def test_generate_then_confirm(self, app):
        with app.app_context():
            tok = token_mod.generate_confirmation_token("user@example.com")
            assert isinstance(tok, str) and tok
            assert token_mod.confirm_token(tok) == "user@example.com"

    def test_confirm_garbage_returns_false(self, app):
        with app.app_context():
            assert token_mod.confirm_token("not-a-real-token") is False

    def test_wrong_salt_rejects(self, app):
        with app.app_context():
            tok = token_mod.generate_confirmation_token("a@b.c")
        # Re-sign with a different salt and verify confirm_token rejects.
        bad = URLSafeTimedSerializer(app.config["SECRET_KEY"]).dumps(
            "a@b.c", salt="different-salt"
        )
        with app.app_context():
            # Token signed with the wrong salt must NOT validate.
            assert token_mod.confirm_token(bad) is False
            # The original token (signed with the correct salt) still validates.
            assert token_mod.confirm_token(tok) == "a@b.c"

    def test_expiration_enforced(self, app):
        with app.app_context():
            tok = token_mod.generate_confirmation_token("a@b.c")
        # itsdangerous uses integer-second timestamps; sleep past it.
        time.sleep(2.1)
        with app.app_context():
            assert token_mod.confirm_token(tok, expiration=1) is False
