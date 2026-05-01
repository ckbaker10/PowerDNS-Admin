import os
basedir = os.path.abspath(os.path.dirname(__file__))

### BASIC APP CONFIG
# TESTING=True flips Flask into test mode AND tells create_app() to
# skip the SECRET_KEY default-value guard, so the public placeholder
# values below are accepted only under this config.
TESTING = True
SALT = '$2b$12$yLUMTIfl21FKJQpTkRQXCu'
SECRET_KEY = 'e951e5a1f4b94151b360f47edf596dd2'
BIND_ADDRESS = '0.0.0.0'
PORT = 9191
HSTS_ENABLED = False

### DATABASE - SQLite
TEST_DB_LOCATION = '/tmp/testing.sqlite'
SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(TEST_DB_LOCATION)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SAML Authnetication
SAML_ENABLED = False

# TEST SAMPLE DATA
TEST_USER = 'test'
TEST_USER_PASSWORD = 'test'
TEST_ADMIN_USER = 'admin'
TEST_ADMIN_PASSWORD = 'admin'
TEST_USER_APIKEY = 'wewdsfewrfsfsdf'
TEST_ADMIN_APIKEY = 'nghnbnhtghrtert'