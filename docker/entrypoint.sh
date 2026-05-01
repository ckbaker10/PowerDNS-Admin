#!/bin/sh
set -euo pipefail
cd /app

GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
GUNICORN_LOGLEVEL="${GUNICORN_LOGLEVEL:-info}"
BIND_ADDRESS="${BIND_ADDRESS:-0.0.0.0:8080}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"

GUNICORN_ARGS="-t ${GUNICORN_TIMEOUT} --workers ${GUNICORN_WORKERS} --bind ${BIND_ADDRESS} --log-level ${GUNICORN_LOGLEVEL}"
if [ "$1" = gunicorn ]; then
    if [ "${RUN_MIGRATIONS}" = "1" ] || [ "${RUN_MIGRATIONS}" = "true" ]; then
        # Serialise schema upgrades across replicas. /data is a per-deployment
        # volume; flock returns immediately for the holder and waits for
        # everyone else, so only one container runs `flask db upgrade` at a
        # time. Set RUN_MIGRATIONS=0 to skip entirely (e.g. when migrations
        # are run by a separate Job).
        if command -v flock >/dev/null 2>&1; then
            flock -w 300 /data/.migrate.lock /bin/sh -c "flask db upgrade"
        else
            /bin/sh -c "flask db upgrade"
        fi
    fi
    exec "$@" $GUNICORN_ARGS

else
    exec "$@"
fi
