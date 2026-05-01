import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name, default):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


# Sentinel value: create_app() refuses to start when SECRET_KEY/SALT still
# match these. Operators MUST override SECRET_KEY (and ideally SALT) via env
# var, FLASK_CONF file, or by editing this file before going to production.
INSECURE_DEFAULT_SECRET_KEY = 'e951e5a1f4b94151b360f47edf596dd2'
INSECURE_DEFAULT_SALT = '$2b$12$yLUMTIfl21FKJQpTkRQXCu'

BIND_ADDRESS = '0.0.0.0'
CAPTCHA_ENABLE = True
CAPTCHA_HEIGHT = 60
CAPTCHA_LENGTH = 6
CAPTCHA_SESSION_KEY = 'captcha_image'
CAPTCHA_WIDTH = 160
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
HSTS_ENABLED = True
PORT = 9191
SALT = os.getenv('SALT', INSECURE_DEFAULT_SALT)
SAML_ASSERTION_ENCRYPTED = True
SAML_ENABLED = False
SECRET_KEY = os.getenv('SECRET_KEY', INSECURE_DEFAULT_SECRET_KEY)
SERVER_EXTERNAL_SSL = _env_bool('SERVER_EXTERNAL_SSL', True)
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_SECURE = True
REMEMBER_COOKIE_HTTPONLY = True
SESSION_TYPE = 'sqlalchemy'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'pdns.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Number of trusted reverse-proxy hops in front of the app. Set to 0 (default)
# when the app is exposed directly; raise it when behind a known proxy chain.
# Keeping this at 0 prevents X-Forwarded-* spoofing from untrusted clients.
PROXY_FIX_X_FOR = int(os.getenv('PROXY_FIX_X_FOR', '0'))
PROXY_FIX_X_PROTO = int(os.getenv('PROXY_FIX_X_PROTO', '0'))
PROXY_FIX_X_HOST = int(os.getenv('PROXY_FIX_X_HOST', '0'))
PROXY_FIX_X_PORT = int(os.getenv('PROXY_FIX_X_PORT', '0'))
PROXY_FIX_X_PREFIX = int(os.getenv('PROXY_FIX_X_PREFIX', '0'))
# SQLA_DB_USER = 'pda'
# SQLA_DB_PASSWORD = 'changeme'
# SQLA_DB_HOST = '127.0.0.1'
# SQLA_DB_NAME = 'pda'
# SQLALCHEMY_DATABASE_URI = 'mysql://{}:{}@{}/{}'.format(
#     urllib.parse.quote_plus(SQLA_DB_USER),
#     urllib.parse.quote_plus(SQLA_DB_PASSWORD),
#     SQLA_DB_HOST,
#     SQLA_DB_NAME
# )
