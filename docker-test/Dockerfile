FROM debian:bookworm-slim
LABEL maintainer="k@ndk.name"

ENV LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 LANGUAGE=en_US.UTF-8

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        build-essential \
        libffi-dev \
        libldap2-dev \
        libmariadb-dev-compat \
        libpq-dev \
        libsasl2-dev \
        libssl-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libxmlsec1-openssl \
        libxslt1-dev \
        locales \
        locales-all \
        pkg-config \
        python3-dev \
        python3-pip \
        python3-setuptools \
    && install -d /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && curl -fsSL https://dl.yarnpkg.com/debian/pubkey.gpg \
        | gpg --dearmor -o /etc/apt/keyrings/yarn.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/yarn.gpg] https://dl.yarnpkg.com/debian/ stable main" \
        > /etc/apt/sources.list.d/yarn.list \
    && apt-get update -y \
    && apt-get install -y --no-install-recommends \
        nodejs \
        yarn \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# We copy just the requirements files first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt
COPY ./requirements-dev.txt /app/requirements-dev.txt

WORKDIR /app
RUN pip3 install --upgrade pip --break-system-packages
RUN pip3 install -r requirements.txt -r requirements-dev.txt --break-system-packages

ENV FLASK_APP=powerdnsadmin/__init__.py

# Layer the COPYs so editing tests/ or docs/ doesn't invalidate the
# (slow) yarn-install and flask-assets-build steps. Order, cheapest
# busting first:
#   1. package.json + yarn.lock -> yarn install        (busts on JS dep change)
#   2. app sources needed by `flask assets build`      (busts on app code change)
#   3. everything else (tests, configs, helpers)       (cheap; busts often)
COPY package.json yarn.lock /app/
RUN yarn install --pure-lockfile --production \
    && yarn cache clean

# `flask assets build` needs to instantiate create_app(), so it
# requires the full powerdnsadmin package + configs + run.py.
# PDA_ALLOW_INSECURE_SECRET_KEY: create_app() refuses to start with
# the shipped placeholder SECRET_KEY. Asset compilation never serves
# traffic, so the check is bypassed only for this build step.
COPY powerdnsadmin/ /app/powerdnsadmin/
COPY configs/ /app/configs/
COPY run.py /app/
RUN ln -s /app/node_modules /app/powerdnsadmin/static/node_modules
RUN PDA_ALLOW_INSECURE_SECRET_KEY=1 flask assets build

# Tests, migrations, docker-test helpers and everything else come
# last so iterating on tests is a no-op rebuild.
COPY . /app

COPY ./docker-test/wait-for-pdns.sh /opt
RUN chmod u+x /opt/wait-for-pdns.sh
CMD ["/opt/wait-for-pdns.sh", "/usr/local/bin/pytest", "-W", "ignore::DeprecationWarning", "--capture=no", "-vv"]
