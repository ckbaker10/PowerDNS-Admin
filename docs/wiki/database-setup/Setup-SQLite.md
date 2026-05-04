# Setup SQLite for PowerDNS-Admin

SQLite is suitable for single-host, low-traffic deployments. No external database server is required — the database is a single file on disk.

## Prepare the host directory

The container runs as the `pda` user (UID 100 / GID 101). You can verify the exact UID/GID from your local image with:

```
docker run --rm --entrypoint '' powerdnsadmin/pda-legacy:latest id pda
```

The host directory that holds the database file must be owned by that UID **before** the container starts, otherwise SQLite will fail with `attempt to write a readonly database`:

```
mkdir -p ./database
chown 100:101 ./database
```

## docker-compose.yml

```yaml
services:
  app:
    image: powerdnsadmin/pda-legacy:latest
    container_name: powerdns_admin
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "127.0.0.1:8082:8080"
    logging:
      driver: json-file
      options:
        max-size: 50m
    volumes:
      - "/etc/localtime:/etc/localtime:ro"
      - "./database/:/database"
    environment:
      - SECRET_KEY='changeme'
      - SQLALCHEMY_DATABASE_URI=sqlite:////database/powerdns-admin.db
      - GUNICORN_TIMEOUT=60
      - GUNICORN_WORKERS=2
      - GUNICORN_LOGLEVEL=DEBUG
      - SALT=changeme
```

Note the four slashes in `sqlite:////database/...` — three are part of the SQLite URI scheme for an absolute path, the fourth begins the container-side path `/database/powerdns-admin.db`.

## Reachability of external services (OIDC / Keycloak)

If the application needs to contact an external auth endpoint (e.g. Keycloak) that is served by the same host's reverse proxy, the container cannot reach it by hostname by default. Add `extra_hosts` to map the hostname to the Docker bridge:

```yaml
    extra_hosts:
      - "your-hostname.example.com:host-gateway"
```

`host-gateway` is a Docker special value that resolves to the host's Docker bridge IP at runtime.
