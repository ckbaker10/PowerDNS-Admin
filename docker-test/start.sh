#!/usr/bin/env sh

if [ -z ${PDNS_API_KEY+x} ]; then
    API_KEY=changeme
fi

if [ -z ${PDNS_PORT+x} ]; then
    WEB_PORT=8081
fi

# Always recreate a fresh database from the SQL schema so that every
# container start (including restarts of a pre-existing container)
# begins with a clean slate. We keep pdns.sql in place so it is
# available for subsequent restarts.
if [ -e "/data/pdns.sql" ]; then
    rm -f /data/pdns.db
    sqlite3 /data/pdns.db < /data/pdns.sql
    echo "Imported schema structure"
fi

chown -R pdns:pdns /data/

/usr/sbin/pdns_server \
    --launch=gsqlite3 --gsqlite3-database=/data/pdns.db \
    --webserver=yes --webserver-address=0.0.0.0 --webserver-port=${PDNS_PORT} \
    --api=yes --api-key=$PDNS_API_KEY --webserver-allow-from=${PDNS_WEBSERVER_ALLOW_FROM}
