"""Smoke tests for the per-request Setting cache helpers.

These tests only exercise the cache primitives (`_get_request_cache` and
`_invalidate_request_cache`) plus `Setting.get()` with the underlying
query monkey-patched away. The full project ``conftest.py`` boots Flask
and isn't usable under Python 3.13 (distutils removal in lib/utils.py),
so we load just the modules we need via importlib.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_setting_module():
    pkg = types.ModuleType("powerdnsadmin")
    pkg.__path__ = [str(REPO_ROOT / "powerdnsadmin")]
    sys.modules.setdefault("powerdnsadmin", pkg)

    lib_pkg = types.ModuleType("powerdnsadmin.lib")
    lib_pkg.__path__ = [str(REPO_ROOT / "powerdnsadmin" / "lib")]
    sys.modules.setdefault("powerdnsadmin.lib", lib_pkg)

    models_pkg = types.ModuleType("powerdnsadmin.models")
    models_pkg.__path__ = [str(REPO_ROOT / "powerdnsadmin" / "models")]
    sys.modules.setdefault("powerdnsadmin.models", models_pkg)

    def _load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
        return m

    _load("powerdnsadmin.lib.settings",
          REPO_ROOT / "powerdnsadmin" / "lib" / "settings.py")
    _load("powerdnsadmin.models.base",
          REPO_ROOT / "powerdnsadmin" / "models" / "base.py")
    return _load("powerdnsadmin.models.setting",
                 REPO_ROOT / "powerdnsadmin" / "models" / "setting.py")


@pytest.fixture()
def setting_env(monkeypatch):
    flask = pytest.importorskip("flask")
    pytest.importorskip("flask_sqlalchemy")
    pytest.importorskip("pytimeparse")

    setting_module = _load_setting_module()
    Setting = setting_module.Setting

    # Replace the SQLAlchemy ``query`` descriptor on the model class so
    # ``Setting.get()`` doesn't try to resolve a real app/DB binding.
    class _Q:
        def filter(self, *a, **k):
            return self
        def first(self):
            return None
    type.__setattr__(Setting, "query", _Q())

    app = flask.Flask(__name__)
    return app, setting_module


def test_get_caches_within_request(setting_env):
    app, setting_module = setting_env
    Setting = setting_module.Setting

    with app.test_request_context("/"):
        s = Setting()
        v1 = s.get("maintenance")
        cache = setting_module._get_request_cache()
        assert cache is not None
        assert "maintenance" in cache
        # Mutate the cache to prove get() reads from it on the next call.
        cache["maintenance"] = "sentinel"
        assert s.get("maintenance") == "sentinel"
        # Sanity: the original computed value was not the sentinel.
        assert v1 != "sentinel"


def test_invalidate_request_cache_drops_keys(setting_env):
    app, setting_module = setting_env

    with app.test_request_context("/"):
        cache = setting_module._get_request_cache()
        cache["a"] = 1
        cache["b"] = 2
        setting_module._invalidate_request_cache("a")
        assert "a" not in cache and cache["b"] == 2
        # No-arg form clears everything.
        setting_module._invalidate_request_cache()
        assert cache == {}


def test_no_cache_outside_request_context(setting_env):
    app, setting_module = setting_env
    with app.app_context():  # app ctx but no request ctx
        assert setting_module._get_request_cache() is None
    # Invalidate is a no-op outside a request — must not raise.
    setting_module._invalidate_request_cache("anything")
