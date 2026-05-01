FROM alpine:3.20 AS builder

ARG BUILD_DEPENDENCIES="build-base \
    libffi-dev \
    libpq-dev \
    libxml2-dev \
    mariadb-connector-c-dev \
    openldap-dev \
    python3-dev \
    xmlsec-dev \
    npm \
    yarn \
    cargo"

ENV LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    FLASK_APP=/build/powerdnsadmin/__init__.py

# Get dependencies
# py3-pip should not belong to BUILD_DEPENDENCIES. Otherwise, when we remove
# them with "apk del" at the end of build stage, the python requests module
# will be removed as well - (Tested with alpine:3.12 and python 3.8.5).
RUN apk add --no-cache ${BUILD_DEPENDENCIES} && \
    apk add --no-cache py3-pip

WORKDIR /build

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /build/requirements.txt

# Build wheels for every runtime dependency. The runtime stage will
# install from this directory with --no-index so no source builds, no
# network access and no toolchain are needed at install time. This
# also pre-bakes binary wheels for python-ldap, lxml, psycopg2, etc.,
# so the runtime image only has to ship the matching shared libraries.
#
# --break-system-packages: Alpine 3.20 ships a PEP 668 marker that
# blocks system-pip writes. We're inside a single-purpose container,
# not a shared OS, so installing into the system site-packages is the
# intended behaviour; a venv would just add a layer of indirection.
RUN pip install --break-system-packages --no-cache-dir --upgrade pip wheel && \
    mkdir -p /wheels && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Install the wheels locally so ``flask assets build`` below can run
# against the resolved dependency set during the build stage.
RUN pip install --break-system-packages --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Add sources
COPY . /build

# Prepare assets
# PDA_ALLOW_INSECURE_SECRET_KEY: ``flask assets build`` instantiates
# the app via create_app(), which refuses to start with the shipped
# placeholder SECRET_KEY. Asset compilation never serves traffic and
# never signs a token, so the check is bypassed only for this build
# step. The runtime stage still enforces it.
RUN PDA_ALLOW_INSECURE_SECRET_KEY=1 \
    yarn install --pure-lockfile --production && \
    yarn cache clean && \
    sed -i -r -e "s|'rcssmin',\s?'cssrewrite'|'rcssmin'|g" /build/powerdnsadmin/assets.py && \
    PDA_ALLOW_INSECURE_SECRET_KEY=1 flask assets build

RUN mv /build/powerdnsadmin/static /tmp/static && \
    mkdir /build/powerdnsadmin/static && \
    cp -r /tmp/static/generated /build/powerdnsadmin/static && \
    cp -r /tmp/static/assets /build/powerdnsadmin/static && \
    cp -r /tmp/static/img /build/powerdnsadmin/static && \
    find /tmp/static/node_modules -name 'webfonts' -exec cp -r {} /build/powerdnsadmin/static \; && \
    find /tmp/static/node_modules -name 'fonts' -exec cp -r {} /build/powerdnsadmin/static \; && \
    find /tmp/static/node_modules/icheck/skins/square -name '*.png' -exec cp {} /build/powerdnsadmin/static/generated \;

RUN { \
      echo "from flask_assets import Environment"; \
      echo "assets = Environment()"; \
      echo "assets.register('js_login', 'generated/login.js')"; \
      echo "assets.register('js_validation', 'generated/validation.js')"; \
      echo "assets.register('css_login', 'generated/login.css')"; \
      echo "assets.register('js_main', 'generated/main.js')"; \
      echo "assets.register('css_main', 'generated/main.css')"; \
    } > /build/powerdnsadmin/assets.py

# Move application
RUN mkdir -p /app && \
    cp -r /build/migrations/ /build/powerdnsadmin/ /build/run.py /app && \
    mkdir -p /app/configs && \
    cp -r /build/configs/docker_config.py /app/configs

# Build image
FROM alpine:3.20

ENV FLASK_APP=/app/powerdnsadmin/__init__.py \
    USER=pda

RUN apk add --no-cache \
        python3 \
        py3-pip \
        mariadb-connector-c \
        postgresql-libs \
        libldap \
        libsasl \
        xmlsec \
        tzdata && \
    addgroup -S ${USER} && \
    adduser -S -D -G ${USER} ${USER} && \
    mkdir /data && \
    chown ${USER}:${USER} /data

# Wheels come from the builder stage. Installing with --no-index +
# --find-links keeps the runtime layer hermetic (no PyPI access, no
# build toolchain) and guarantees the versions match requirements.txt.
# We deliberately do NOT install Alpine's py3-gunicorn/py3-flask/
# py3-pyldap/py3-psycopg2: those packages would shadow our pins and
# silently downgrade CVE fixes for gunicorn, requests, etc.
COPY --from=builder /wheels /wheels
COPY --from=builder /build/requirements.txt /tmp/requirements.txt
RUN pip install --break-system-packages --no-cache-dir --no-index --find-links=/wheels \
        -r /tmp/requirements.txt && \
    rm -rf /wheels /tmp/requirements.txt /root/.cache

# The ``flask`` console script is installed by the Flask wheel above,
# so we no longer need to copy it from the builder stage.
COPY --from=builder --chown=root:${USER} /app /app/
COPY ./docker/entrypoint.sh /usr/bin/

WORKDIR /app
RUN chown ${USER}:${USER} ./configs /app && \
    cat ./powerdnsadmin/default_config.py ./configs/docker_config.py > ./powerdnsadmin/docker_config.py

# Bind to an unprivileged port inside the container; orchestrators publish
# host:80 -> container:8080 without needing CAP_NET_BIND_SERVICE.
EXPOSE 8080/tcp
USER ${USER}
HEALTHCHECK --interval=5s --timeout=5s --start-period=20s --retries=5 CMD wget --output-document=- --quiet --tries=1 http://127.0.0.1:8080${SCRIPT_NAME:-/}
ENTRYPOINT ["entrypoint.sh"]
CMD ["gunicorn","powerdnsadmin:create_app()"]
