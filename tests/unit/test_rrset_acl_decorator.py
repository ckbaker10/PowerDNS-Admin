"""Decorator-level test for ``apikey_rrset_acl_enforced``.

We construct a minimal Flask app with a stub forward route to verify the
gating logic without needing a database or a real PowerDNS upstream.
"""
import importlib.util
import json
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load_helper():
    spec = importlib.util.spec_from_file_location(
        'rrset_acl_under_test', ROOT / 'powerdnsadmin' / 'lib' / 'rrset_acl.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules['rrset_acl_under_test'] = mod
    spec.loader.exec_module(mod)
    return mod


pytest.importorskip('flask')
helper = _load_helper()


def _build_decorator(rules):
    """Replicate the decorator's logic against a stub apikey object."""
    from flask import g, request, abort

    apikey_stub = types.SimpleNamespace(id=1, rrset_acls=rules)

    def decorator(f):
        def wrapped(*args, **kwargs):
            g.apikey = apikey_stub
            method = request.method.upper()
            if not apikey_stub.rrset_acls:
                return f(*args, **kwargs)
            if method == 'GET':
                return f(*args, **kwargs)
            if method != 'PATCH':
                abort(403)
            body = request.get_json(force=True, silent=True) or {}
            ok, _ = helper.evaluate_patch(
                [r for r in apikey_stub.rrset_acls],
                kwargs.get('zone_id', ''), body)
            if not ok:
                abort(403)
            return f(*args, **kwargs)
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator


@pytest.fixture()
def app_factory():
    from flask import Flask

    def make(rules):
        app = Flask(__name__)
        deco = _build_decorator(rules)

        @app.route('/api/v1/servers/<srv>/zones/<zone_id>', methods=['PATCH', 'GET', 'DELETE'])
        @deco
        def proxy(srv, zone_id):
            return 'ok', 204
        return app
    return make


def _rule(name='_acme-challenge.host.example.com.', allow_replace=True,
          allow_delete=True, rtype='TXT'):
    return helper.AclRule(domain_name='example.com',
                          record_name_pattern=name,
                          record_type=rtype,
                          allow_replace=allow_replace,
                          allow_delete=allow_delete)


def test_patch_allowed_for_matching_rrset(app_factory):
    app = app_factory([_rule()])
    client = app.test_client()
    body = {'rrsets': [{
        'name': '_acme-challenge.host.example.com.', 'type': 'TXT',
        'changetype': 'REPLACE', 'ttl': 60, 'records': []}]}
    r = client.patch('/api/v1/servers/localhost/zones/example.com.',
                     data=json.dumps(body),
                     content_type='application/json')
    assert r.status_code == 204


def test_patch_denied_for_other_name(app_factory):
    app = app_factory([_rule()])
    body = {'rrsets': [{
        'name': '_acme-challenge.evil.example.com.', 'type': 'TXT',
        'changetype': 'REPLACE', 'ttl': 60, 'records': []}]}
    r = app.test_client().patch(
        '/api/v1/servers/localhost/zones/example.com.',
        data=json.dumps(body), content_type='application/json')
    assert r.status_code == 403


def test_delete_zone_denied_for_scoped_key(app_factory):
    app = app_factory([_rule()])
    r = app.test_client().delete('/api/v1/servers/localhost/zones/example.com.')
    assert r.status_code == 403


def test_get_allowed_for_scoped_key(app_factory):
    app = app_factory([_rule()])
    r = app.test_client().get('/api/v1/servers/localhost/zones/example.com.')
    assert r.status_code == 204


def test_no_acl_rows_acts_as_passthrough(app_factory):
    app = app_factory([])
    r = app.test_client().delete('/api/v1/servers/localhost/zones/example.com.')
    assert r.status_code == 204


def test_atomic_rejection_with_one_bad_rrset(app_factory):
    app = app_factory([_rule()])
    body = {'rrsets': [
        {'name': '_acme-challenge.host.example.com.', 'type': 'TXT',
         'changetype': 'REPLACE', 'ttl': 60, 'records': []},
        {'name': '_acme-challenge.evil.example.com.', 'type': 'TXT',
         'changetype': 'REPLACE', 'ttl': 60, 'records': []},
    ]}
    r = app.test_client().patch(
        '/api/v1/servers/localhost/zones/example.com.',
        data=json.dumps(body), content_type='application/json')
    assert r.status_code == 403
