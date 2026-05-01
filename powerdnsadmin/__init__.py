import os
import logging
from flask import Flask
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_session import Session
from .lib import utils


def create_app(config=None):
    from powerdnsadmin.lib.settings import AppSettings
    from . import models, routes, services
    from .assets import assets
    app = Flask(__name__)

    # Read log level from environment variable
    log_level_name = os.environ.get('PDNS_ADMIN_LOG_LEVEL', 'WARNING')
    log_level = logging.getLevelName(log_level_name.upper())
    # Setting logger
    logging.basicConfig(
       level=log_level,
        format=
        "[%(asctime)s] [%(filename)s:%(lineno)d] %(levelname)s - %(message)s")

    # If we use Docker + Gunicorn, adjust the
    # log handler
    if "GUNICORN_LOGLEVEL" in os.environ:
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    # Proxy
    # ProxyFix is wired up after the config has been loaded so the trust-hop
    # counts are honoured. Defaults are 0, which leaves request metadata
    # untouched and prevents X-Forwarded-* spoofing from untrusted clients.

    # Load config from env variables if using docker
    if os.path.exists(os.path.join(app.root_path, 'docker_config.py')):
        app.config.from_object('powerdnsadmin.docker_config')
    else:
        # Load default configuration
        app.config.from_object('powerdnsadmin.default_config')

    # Load config file from FLASK_CONF env variable
    if 'FLASK_CONF' in os.environ:
        app.config.from_envvar('FLASK_CONF')

    # Load app specified configuration
    if config is not None:
        if isinstance(config, dict):
            app.config.update(config)
        elif config.endswith('.py'):
            app.config.from_pyfile(config)

    # Load any settings defined with environment variables
    AppSettings.load_environment(app)

    # Refuse to start with the shipped placeholder SECRET_KEY/SALT in any
    # non-testing context. These constants are public (they are checked into
    # the source tree) so leaving them in place would let any reader forge
    # signed sessions, password-reset tokens and CSRF tokens.
    from .default_config import (
        INSECURE_DEFAULT_SECRET_KEY,
        INSECURE_DEFAULT_SALT,
    )
    allow_insecure = (
        app.config.get('TESTING')
        or os.environ.get('PDA_ALLOW_INSECURE_SECRET_KEY', '').lower()
        in ('1', 'true', 'yes')
    )
    if not allow_insecure:
        if app.config.get('SECRET_KEY') == INSECURE_DEFAULT_SECRET_KEY:
            raise RuntimeError(
                "Refusing to start: SECRET_KEY is still the shipped default. "
                "Set the SECRET_KEY environment variable (or override it in "
                "your config file) to a long, random value before starting "
                "PowerDNS-Admin. Generate one with: "
                "python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        if app.config.get('SALT') == INSECURE_DEFAULT_SALT:
            app.logger.warning(
                "SALT is still the shipped default. Override the SALT "
                "environment variable to invalidate previously-issued "
                "password-reset and email-confirmation tokens."
            )

    # Apply ProxyFix only when the operator has explicitly trusted at least
    # one upstream hop. Without this guard, a direct client could spoof
    # X-Forwarded-For and bypass any IP-based controls downstream.
    proxy_hops = max(
        app.config.get('PROXY_FIX_X_FOR', 0),
        app.config.get('PROXY_FIX_X_PROTO', 0),
        app.config.get('PROXY_FIX_X_HOST', 0),
        app.config.get('PROXY_FIX_X_PORT', 0),
        app.config.get('PROXY_FIX_X_PREFIX', 0),
    )
    if proxy_hops > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_FIX_X_FOR', 0),
            x_proto=app.config.get('PROXY_FIX_X_PROTO', 0),
            x_host=app.config.get('PROXY_FIX_X_HOST', 0),
            x_port=app.config.get('PROXY_FIX_X_PORT', 0),
            x_prefix=app.config.get('PROXY_FIX_X_PREFIX', 0),
        )

    # HSTS
    if app.config.get('HSTS_ENABLED'):
        from flask_sslify import SSLify
        _sslify = SSLify(app)  # lgtm [py/unused-local-variable]

    # Load Flask-Session
    app.config['SESSION_TYPE'] = app.config.get('SESSION_TYPE')
    if 'SESSION_TYPE' in os.environ:
        app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE')

    sess = Session(app)

    # create sessions table if using sqlalchemy backend. Read from
    # app.config (not os.environ) so the table is also created when
    # SESSION_TYPE is supplied via the config file rather than an env
    # var — otherwise the integration test image (and any deployment
    # that relies on default_config.SESSION_TYPE) ends up without the
    # 'sessions' table and every authenticated request 500s.
    if app.config.get('SESSION_TYPE') == 'sqlalchemy':
        with app.app_context():
            sess.app.session_interface.db.create_all()

    # SMTP
    app.mail = Mail(app)

    # Load app's components
    assets.init_app(app)
    models.init_app(app)
    routes.init_app(app)
    services.init_app(app)

    # Register filters
    app.jinja_env.filters['display_record_name'] = utils.display_record_name
    app.jinja_env.filters['display_master_name'] = utils.display_master_name
    app.jinja_env.filters['display_second_to_time'] = utils.display_time
    app.jinja_env.filters['display_setting_state'] = utils.display_setting_state
    app.jinja_env.filters['pretty_domain_name'] = utils.pretty_domain_name
    app.jinja_env.filters['format_datetime_local'] = utils.format_datetime
    app.jinja_env.filters['format_zone_type'] = utils.format_zone_type

    # Register context processors
    from .models.setting import Setting

    @app.context_processor
    def inject_sitename():
        setting = Setting().get('site_name')
        return dict(SITE_NAME=setting)

    @app.context_processor
    def inject_setting():
        setting = Setting()
        return dict(SETTING=setting)

    return app
