This describes how to run Apache2 on the host system with a reverse proxy directing to the docker container

This is usually used to add ssl certificates and prepend a subdirectory

The network_mode host settings is not neccessary but used for ldap availability in this case

## docker-compose.yml

### With MySQL / MariaDB

```
version: "3"
services:
  app:
    image: powerdnsadmin/pda-legacy:latest
    container_name: powerdns
    restart: always
    network_mode: "host"
    logging:
      driver: json-file
      options:
        max-size: 50m
    environment:
      - BIND_ADDRESS=127.0.0.1:8082
      - SECRET_KEY='NotVerySecret'
      - SQLALCHEMY_DATABASE_URI=mysql://pdnsadminuser:password@127.0.0.1/powerdnsadmin
      - GUNICORN_TIMEOUT=60
      - GUNICORN_WORKERS=2
      - GUNICORN_LOGLEVEL=DEBUG
      - OFFLINE_MODE=False
      - CSRF_COOKIE_SECURE=False
      - PROXY_FIX_X_PROTO=1
      - PROXY_FIX_X_PREFIX=1
```

See the [SQLite setup guide](../database-setup/Setup-SQLite.md) for database preparation steps, including the required host directory ownership fix and `extra_hosts` configuration for OIDC endpoints.

## Apache reverse proxy configuration

### Required modules

```
a2enmod proxy proxy_http headers
```

### X-Forwarded-* headers and prefix stripping

The application uses Werkzeug's `ProxyFix` middleware to reconstruct correct absolute URLs
behind a reverse proxy. The following env vars (set in `docker-compose.yml`) control how many
trusted upstream hops are accepted:

| env var              | purpose                                              |
|----------------------|------------------------------------------------------|
| `PROXY_FIX_X_PROTO`  | trust `X-Forwarded-Proto` (http → https scheme)      |
| `PROXY_FIX_X_PREFIX` | trust `X-Forwarded-Prefix` (strip subpath prefix)    |

> **Important:** Use `X-Forwarded-Prefix`, **not** `SCRIPT_NAME`, in the Apache `RequestHeader`
> directive. Werkzeug reads `X-Forwarded-Prefix`; setting `SCRIPT_NAME` has no effect.

> **Important:** The `ProxyPass` target must **not** include the subpath (e.g. use
> `http://127.0.0.1:8082`, not `http://127.0.0.1:8082/powerdns`). Apache must strip the prefix
> before forwarding so Flask receives requests at `/`, `/login`, etc.

> **Important:** Add `disablereuse=On` to `ProxyPass`. Without it, Apache pools the backend
> connection with keepalive; gunicorn's sync workers block waiting for the next request on the
> idle connection and time out after 60 s, causing WORKER TIMEOUT errors and very slow responses.

```apache
    <Location /powerdns>
        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Forwarded-Port "443"
        RequestHeader set X-Forwarded-Prefix "/powerdns"
        ProxyPreserveHost On
    </Location>

    ProxyPass /powerdns http://127.0.0.1:8082 disablereuse=On
    ProxyPassReverse /powerdns http://127.0.0.1:8082
```

After running the Container create the static directory and populate

```
mkdir -p /var/www/powerdns
docker cp powerdns:/app/powerdnsadmin/static /var/www/powerdns/
chown -R root:www-data /var/www/powerdns
```

Adjust the static reference, static/assets/css has a hardcoded reference

```
sed -i 's/\/static/\/powerdns\/static/' /var/www/powerdns/static/assets/css/*
```

Optionally serve static files directly from Apache to reduce gunicorn load:

```apache
    ProxyPass /powerdns/static !

    Alias /powerdns/static "/var/www/powerdns/static"

    <Directory "/var/www/powerdns/static">
        Options None
        AllowOverride None
        Order allow,deny
        Allow from all
    </Directory>
```

## Trusting a private / internal CA for outbound TLS (OIDC, LDAP, etc.)

When the container makes outbound HTTPS requests — for example fetching the OIDC provider's
`.well-known/openid-configuration` — it uses the CA bundle bundled inside the image. If your
reverse proxy (Keycloak, etc.) is signed by an internal CA that is not in that bundle, you will
see:

```
ssl.SSLCertVerificationError: certificate verify failed: unable to get local issuer certificate
```

The fix is to bind-mount the host's CA bundle over the `certifi` bundle inside the container.

### Find the correct path inside your image

The path depends on the Python version shipped in the image. Run this to get the exact paths:

```
docker run --rm --entrypoint '' powerdnsadmin/pda-legacy:latest \
  python3 -c "import certifi, requests.certs; print(certifi.where()); print(requests.certs.where())"
```

Both `certifi` and `requests` typically point to the same file. For Alpine 3.20 / Python 3.12
this is `/usr/lib/python3.12/site-packages/certifi/cacert.pem`.

### docker-compose.yml volume mount

Mount the host's combined CA bundle (which must include your internal CA) over the path found above:

```yaml
    volumes:
      - "/etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro"
      - "/etc/ssl/certs/ca-certificates.crt:/usr/lib/python3.12/site-packages/certifi/cacert.pem:ro"
```

If you update your host's CA store (`update-ca-certificates`), the new bundle is picked up
automatically on the next container restart — no image rebuild needed.