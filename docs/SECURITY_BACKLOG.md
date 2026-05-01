# Remaining Security Issues

This page tracks known security advisories that are **not yet fixed**
in `requirements.txt`. Each one is currently suppressed in CI via
`pip-audit --ignore-vuln` (see [.github/workflows/ci.yml](../.github/workflows/ci.yml))
because the only available fix requires a major-version upgrade of a
core dependency. Those upgrades are intrusive (Flask 2 → 3,
Werkzeug 2 → 3, SQLAlchemy 1.4 → 2, etc.) and are tracked as separate
work items in the project audit.

> **Status legend**
> - **Suppressed** — listed in `--ignore-vuln`; CI is green but the
>   vulnerability is still present in the shipped image.
> - **Mitigated** — runtime configuration or code makes the issue
>   unreachable in practice.
> - **Accepted** — false-positive for our deployment model.

When any of the upgrades below lands, remove the matching
`--ignore-vuln` line from CI and delete the corresponding row here.

## Major dependency upgrades required

### Authlib → 1.6.x (OIDC / OAuth library)

Currently pinned at `1.3.1`.

| Advisory             | Status     | Fixed in    |
|----------------------|------------|-------------|
| CVE-2025-59420       | Suppressed | Authlib 1.6 |
| CVE-2025-61920       | Suppressed | Authlib 1.6 |
| CVE-2025-62706       | Suppressed | Authlib 1.6 |
| CVE-2025-68158       | Suppressed | Authlib 1.6 |
| CVE-2026-27962       | Suppressed | Authlib 1.6 |
| CVE-2026-28490       | Suppressed | Authlib 1.6 |
| GHSA-jj8c-mmj3-mmgv  | Suppressed | Authlib 1.6 |

**Impact:** OIDC/OAuth login flow only. Sites that authenticate
exclusively via local accounts, LDAP or SAML are unaffected.

### Flask → 3.x

Currently pinned at `2.2.5` (EOL upstream).

| Advisory       | Status     | Fixed in |
|----------------|------------|----------|
| CVE-2026-27205 | Suppressed | Flask 3  |

**Blocker:** Flask 3 also forces Werkzeug 3, Jinja 3.1+, and a
matching Flask-SQLAlchemy / Flask-Login / Flask-Migrate refresh.

### Werkzeug → 3.x

Currently pinned at `2.3.8`.

| Advisory       | Status     | Fixed in   |
|----------------|------------|------------|
| CVE-2024-34069 | Suppressed | Werkzeug 3 |
| CVE-2024-49766 | Suppressed | Werkzeug 3 |
| CVE-2024-49767 | Suppressed | Werkzeug 3 |
| CVE-2025-66221 | Suppressed | Werkzeug 3 |
| CVE-2026-21860 | Suppressed | Werkzeug 3 |
| CVE-2026-27199 | Suppressed | Werkzeug 3 |

**Mitigation in place:** the application sits behind a reverse proxy
in every supported deployment (Docker, Kubernetes, manual setup);
several of the Werkzeug findings only apply to the embedded debug
server, which is never used in production.

### cryptography → 46.x

Currently pinned at `44.0.1`.

| Advisory       | Status     | Fixed in        |
|----------------|------------|-----------------|
| CVE-2026-26007 | Suppressed | cryptography 46 |
| CVE-2026-34073 | Suppressed | cryptography 46 |

### lxml → 6.x

Currently pinned at `4.9.4`.

| Advisory       | Status     | Fixed in |
|----------------|------------|----------|
| CVE-2026-41066 | Suppressed | lxml 6   |

**Impact:** XML parsing path used by the SAML integration.

### pyasn1 → 0.6.x

| Advisory       | Status     | Fixed in   |
|----------------|------------|------------|
| CVE-2026-30922 | Suppressed | pyasn1 0.6 |

### requests → 2.33.x

Currently pinned at `2.32.4`.

| Advisory       | Status     | Fixed in     |
|----------------|------------|--------------|
| CVE-2026-25645 | Suppressed | requests 2.33|

## Mitigated / accepted findings

| Item                                                  | Where                                                                    | Status    | Notes                                                                                                          |
|-------------------------------------------------------|--------------------------------------------------------------------------|-----------|----------------------------------------------------------------------------------------------------------------|
| `BIND_ADDRESS = '0.0.0.0'` (Bandit B104)              | [powerdnsadmin/default_config.py](../powerdnsadmin/default_config.py), [powerdnsadmin/lib/settings.py](../powerdnsadmin/lib/settings.py) | Accepted  | Intentional in-container bind; the orchestrator publishes the port. Marked `# nosec B104` with justification. |

## How to verify locally

```bash
# Lint + security gates (mirrors CI):
ruff check --select F,B,W6 --ignore B006,B904,B905,B007 powerdnsadmin
bandit -r powerdnsadmin -ll -x powerdnsadmin/tests
pip-audit --strict -r requirements.txt   # add the same --ignore-vuln flags as CI to match
```

If `pip-audit` reports a CVE that is **not** in the table above, treat
it as a regression and fix it (or document it here) before merging.
