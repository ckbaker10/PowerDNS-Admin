# PowerDNS-Admin

A PowerDNS web interface with advanced features.

[![CodeQL](https://github.com/PowerDNS-Admin/PowerDNS-Admin/actions/workflows/codeql-analysis.yml/badge.svg?branch=master)](https://github.com/PowerDNS-Admin/PowerDNS-Admin/actions/workflows/codeql-analysis.yml)
[![Docker Image](https://github.com/PowerDNS-Admin/PowerDNS-Admin/actions/workflows/build-and-publish.yml/badge.svg?branch=master)](https://github.com/PowerDNS-Admin/PowerDNS-Admin/actions/workflows/build-and-publish.yml)

#### Features:

- Provides forward and reverse zone management
- Provides zone templating features
- Provides user management with role based access control
- Provides zone specific access control
- Provides activity logging
- Authentication:
  - Local User Support
  - SAML Support
  - LDAP Support: OpenLDAP / Active Directory
  - OAuth Support: Google / GitHub / Azure / OpenID
- Two-factor authentication support (TOTP)
- PDNS Service Configuration & Statistics Monitoring
- DynDNS 2 protocol support
- Easy IPv6 PTR record editing
- Provides an API for zone and record management among other features
- Provides record-scoped API keys for fine-grained automation (e.g. certbot DNS-01)
- Provides full IDN/Punycode support

## [Project Update - PLEASE READ!!!](https://github.com/PowerDNS-Admin/PowerDNS-Admin/discussions/1708)

## Running PowerDNS-Admin

There are several ways to run PowerDNS-Admin. The quickest way is to use Docker.
If you are looking to install and run PowerDNS-Admin directly onto your system, check out
the [wiki](https://github.com/PowerDNS-Admin/PowerDNS-Admin/blob/master/docs/wiki/) for ways to do that.

### Docker

Here are two options to run PowerDNS-Admin using Docker.
To get started as quickly as possible, try option 1. If you want to make modifications to the configuration option 2 may
be cleaner.

#### Option 1: From Docker Hub

To run the application using the latest stable release on Docker Hub, run the following command:

```
$ docker run -d \
    -e SECRET_KEY='a-very-secret-key' \
    -v pda-data:/data \
    -p 9191:80 \
    powerdnsadmin/pda-legacy:latest
```

This creates a volume named `pda-data` to persist the default SQLite database with app configuration.

#### Option 2: Using docker-compose

1. Update the configuration   
   Edit the `docker-compose.yml` file to update the database connection string in `SQLALCHEMY_DATABASE_URI`.
   Other environment variables are mentioned in
   the [AppSettings.defaults](https://github.com/PowerDNS-Admin/PowerDNS-Admin/blob/master/powerdnsadmin/lib/settings.py) dictionary.
   To use a Docker-style secrets convention, one may append `_FILE` to the environment variables with a path to a file
   containing the intended value of the variable (e.g. `SQLALCHEMY_DATABASE_URI_FILE=/run/secrets/db_uri`).   
   Make sure to set the environment variable `SECRET_KEY` to a long, random
   string (https://flask.palletsprojects.com/en/1.1.x/config/#SECRET_KEY)

2. Start docker container
   ```
   $ docker-compose up
   ```

You can then access PowerDNS-Admin by pointing your browser to http://localhost:9191.

## Screenshots

![dashboard](docs/screenshots/dashboard.png)

## Record-scoped API keys (certbot DNS-01)

PowerDNS-Admin can mint API keys that are restricted to specific RRsets within
a zone. These keys may only PATCH the rrsets that match their ACL rules; any
other rrset, and any zone-level write (POST/PUT/DELETE), is rejected before
the request reaches PowerDNS. Read access is still scoped to the key's zones
via the existing zone-level authorisation.

The intended use case is automated certificate issuance: the
[certbot-dns-pdns](https://github.com/kaechele/certbot-dns-pdns) plugin speaks
the standard PowerDNS HTTP API. Pointing it at PowerDNS-Admin's `/api/v1`
proxy with a record-scoped key restricts a renewal job to the single
`_acme-challenge.<host>` TXT rrset it actually needs to update. PowerDNS
itself does not need to be reachable from the certbot host.

### Creating a scoped key

Open *Admin -> API Keys -> Create Key* (or click the *Let's Encrypt Key*
button on a zone page for a one-click prefilled form). In the *Restrict to
Specific Records* section, add a row per RRset the key should be allowed to
modify:

| Zone | Name pattern | Type | REPLACE | DELETE |
|------|--------------|------|---------|--------|
| example.com | `_acme-challenge.host.example.com.` | TXT | yes | yes |

Patterns are exact FQDNs or use a single `*` as a complete label
(`_acme-challenge.*.example.com.` matches one label).

### Permissions

| Caller role | Unscoped key | Scoped key | Allowed scopes |
|-------------|--------------|------------|----------------|
| Administrator | yes | yes | any zone, any record name, any type |
| Operator | yes | yes | any zone, any record name, any type |
| User (zone owner) | no | yes | only zones they own; only TXT by default |

The User-role behaviour is gated by the `allow_user_create_scoped_apikey`
setting (default on) under *Admin -> Settings -> Basic*.

### certbot setup

Install the `certbot-dns-pdns` plugin on the machine that runs certbot:

```bash
# pip / virtualenv
pip install certbot-dns-pdns

# snap (most common on Ubuntu 20.04+)
sudo snap install certbot-dns-pdns
sudo snap connect certbot:plugin certbot-dns-pdns

# Debian / Ubuntu apt
sudo apt install python3-certbot-dns-pdns
```

Verify the plugin is registered:

```bash
certbot plugins   # should list: dns-pdns
```

Create a credentials file and lock its permissions:

```bash
chmod 600 /etc/letsencrypt/pdns-credentials.ini
```

```ini
# /etc/letsencrypt/pdns-credentials.ini
dns_pdns_endpoint        = https://pdnsadmin.example.com
dns_pdns_api_key         = <scoped-key from PowerDNS-Admin UI>
dns_pdns_server_id       = localhost
dns_pdns_disable_notify  = true
```

> `dns_pdns_disable_notify` suppresses secondary-nameserver notifications after the
> challenge record is written. Set to `true` for a single authoritative server, `false`
> if you want secondaries notified. The property is required — omitting it causes certbot
> to abort with "Missing property".

Then request a certificate:

```bash
certbot certonly \
  --authenticator dns-pdns \
  --dns-pdns-credentials /etc/letsencrypt/pdns-credentials.ini \
  -d host.example.com
```

> **Note:** `-d` is the domain you want the **certificate for** (e.g. `host.example.com`).
> Do **not** pass the `_acme-challenge` subdomain — the plugin creates that TXT record
> automatically. Passing `_acme-challenge.host.example.com` will cause Let's Encrypt to
> reject the request with "Domain name contains an invalid character".

The key may only touch `_acme-challenge.host.example.com./TXT`. A
compromised credential cannot be used to alter any other record.

## Support

**Looking for help?** Try taking a look at the project's
[Support Guide](https://github.com/PowerDNS-Admin/PowerDNS-Admin/blob/master/.github/SUPPORT.md) or joining
our [Discord Server](https://discord.powerdnsadmin.org).

## Security Policy

Please see our [Security Policy](https://github.com/PowerDNS-Admin/PowerDNS-Admin/blob/master/SECURITY.md).

For the list of known advisories that are still open against the
pinned dependencies (and the major-version upgrades required to clear
them), see [docs/SECURITY_BACKLOG.md](docs/SECURITY_BACKLOG.md).

## Contributing

Please see our [Contribution Guide](https://github.com/PowerDNS-Admin/PowerDNS-Admin/blob/master/docs/CONTRIBUTING.md).

## Code of Conduct

Please see our [Code of Conduct Policy](https://github.com/PowerDNS-Admin/PowerDNS-Admin/blob/master/docs/CODE_OF_CONDUCT.md).

## License

This project is released under the MIT license. For additional
information, [see the full license](https://github.com/PowerDNS-Admin/PowerDNS-Admin/blob/master/LICENSE).
