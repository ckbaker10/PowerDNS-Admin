import sys
import traceback
import pytimeparse
from ast import literal_eval
from flask import current_app, g, has_request_context
from .base import db
from powerdnsadmin.lib.settings import AppSettings


_REQUEST_CACHE_KEY = '_pda_settings_cache'


def _get_request_cache():
    """Return the per-request settings cache (a dict).

    Settings are read dozens of times per request (api_url, api_key,
    timeouts, verify_ssl, ...). Each ``Setting().get()`` call hits the
    DB. Caching them on ``flask.g`` for the life of one request removes
    that hot path completely. The cache is a dict keyed by setting name
    and is populated lazily on first ``get()``. Any ``set()``/``toggle()``
    invalidates the affected key so writes during the same request are
    visible.

    Outside a request context (CLI, ``flask db upgrade``, tests), this
    returns ``None`` and ``Setting.get()`` falls back to a direct query.
    """
    if not has_request_context():
        return None
    cache = g.get(_REQUEST_CACHE_KEY, None)
    if cache is None:
        cache = {}
        setattr(g, _REQUEST_CACHE_KEY, cache)
    return cache


def _invalidate_request_cache(*setting_names):
    cache = _get_request_cache()
    if cache is None:
        return
    if not setting_names:
        cache.clear()
        return
    for name in setting_names:
        cache.pop(name, None)



class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    value = db.Column(db.Text())

    ZONE_TYPE_FORWARD = 'forward'
    ZONE_TYPE_REVERSE = 'reverse'

    def __init__(self, id=None, name=None, value=None):
        self.id = id
        self.name = name
        self.value = value

    # allow database autoincrement to do its own ID assignments
    def __init__(self, name=None, value=None):
        self.id = None
        self.name = name
        self.value = value

    def set_maintenance(self, mode):
        maintenance = Setting.query.filter(
            Setting.name == 'maintenance').first()

        if maintenance is None:
            value = AppSettings.defaults['maintenance']
            maintenance = Setting(name='maintenance', value=str(value))
            db.session.add(maintenance)

        mode = str(mode)

        try:
            if maintenance.value != mode:
                maintenance.value = mode
                db.session.commit()
            _invalidate_request_cache('maintenance')
            return True
        except Exception as e:
            current_app.logger.error('Cannot set maintenance to {0}. DETAIL: {1}'.format(
                mode, e))
            current_app.logger.debug(traceback.format_exec())
            db.session.rollback()
            return False

    def toggle(self, setting):
        current_setting = Setting.query.filter(Setting.name == setting).first()

        if current_setting is None:
            value = AppSettings.defaults[setting]
            current_setting = Setting(name=setting, value=str(value))
            db.session.add(current_setting)

        try:
            if current_setting.value == "True":
                current_setting.value = "False"
            else:
                current_setting.value = "True"
            db.session.commit()
            _invalidate_request_cache(setting)
            return True
        except Exception as e:
            current_app.logger.error('Cannot toggle setting {0}. DETAIL: {1}'.format(
                setting, e))
            current_app.logger.debug(traceback.format_exec())
            db.session.rollback()
            return False

    def set(self, setting, value):
        import json
        current_setting = Setting.query.filter(Setting.name == setting).first()

        if current_setting is None:
            current_setting = Setting(name=setting, value=None)
            db.session.add(current_setting)

        value = AppSettings.convert_type(setting, value)

        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value)

        try:
            current_setting.value = value
            db.session.commit()
            _invalidate_request_cache(setting)
            return True
        except Exception as e:
            current_app.logger.error('Cannot edit setting {0}. DETAIL: {1}'.format(setting, e))
            current_app.logger.debug(traceback.format_exec())
            db.session.rollback()
            return False

    def get(self, setting):
        if setting in AppSettings.defaults:

            cache = _get_request_cache()
            if cache is not None and setting in cache:
                return cache[setting]

            if setting.upper() in current_app.config:
                result = current_app.config[setting.upper()]
            else:
                result = self.query.filter(Setting.name == setting).first()

            if result is not None:
                if hasattr(result, 'value'):
                    result = result.value

                value = AppSettings.convert_type(setting, result)
            else:
                value = AppSettings.defaults[setting]

            # Hard floor for outbound timeouts: 0/None lets requests block
            # forever and pin a gunicorn worker if PDNS hangs.
            if setting == 'pdns_api_timeout':
                try:
                    value = max(int(value or 0), 5)
                except (TypeError, ValueError):
                    value = 30

            if cache is not None:
                cache[setting] = value
            return value
        else:
            current_app.logger.error('Unknown setting queried: {0}'.format(setting))

    def get_group(self, group):
        if not isinstance(group, list):
            group = AppSettings.groups[group]

        result = {}

        for var_name, default_value in AppSettings.defaults.items():
            if var_name in group:
                result[var_name] = self.get(var_name)

        return result

    def get_records_allow_to_edit(self):
        return list(
            set(self.get_supported_record_types(self.ZONE_TYPE_FORWARD) +
                self.get_supported_record_types(self.ZONE_TYPE_REVERSE)))

    def get_supported_record_types(self, zone_type):
        setting_value = []

        if zone_type == self.ZONE_TYPE_FORWARD:
            setting_value = self.get('forward_records_allow_edit')
        elif zone_type == self.ZONE_TYPE_REVERSE:
            setting_value = self.get('reverse_records_allow_edit')

        records = literal_eval(setting_value) if isinstance(setting_value, str) else setting_value
        types = [r for r in records if records[r]]

        # Sort alphabetically if python version is smaller than 3.6
        if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 6):
            types.sort()

        return types

    def get_ttl_options(self):
        return [(pytimeparse.parse(ttl), ttl)
                for ttl in self.get('ttl_options').split(',')]
