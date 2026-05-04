"""Pure-function ACL evaluator for record-scoped API keys.

Used by both the request-time decorator and the mint-endpoint validator.
Kept free of Flask/SQLAlchemy imports for easy unit testing.
"""
from typing import Iterable, Tuple


def _normalise(name: str) -> str:
    """Lowercase, strip exactly one trailing dot."""
    if not name:
        return ''
    n = name.lower()
    if n.endswith('.'):
        n = n[:-1]
    return n


def match_pattern(pattern: str, name: str) -> bool:
    """Match a record name against an ACL pattern.

    Grammar:
      - Exact: ``_acme-challenge.host.example.com[.]`` (case-insensitive,
        trailing dot optional).
      - One ``*`` allowed and only as a complete label, matching exactly
        one label: ``_acme-challenge.*.example.com`` matches
        ``_acme-challenge.host.example.com`` but not
        ``_acme-challenge.a.b.example.com``.
    """
    p_labels = _normalise(pattern).split('.')
    n_labels = _normalise(name).split('.')

    if len(p_labels) != len(n_labels):
        return False
    for pl, nl in zip(p_labels, n_labels):
        if pl == '*':
            if not nl:
                return False
            continue
        if '*' in pl:
            # `*` only allowed as a full label, never partial.
            return False
        if pl != nl:
            return False
    return True


class AclRule:
    """Lightweight value object so this module can be tested without
    pulling in the SQLAlchemy model."""
    __slots__ = ('domain_name', 'record_name_pattern', 'record_type',
                 'allow_replace', 'allow_delete')

    def __init__(self, domain_name, record_name_pattern, record_type,
                 allow_replace=True, allow_delete=True):
        self.domain_name = _normalise(domain_name)
        self.record_name_pattern = record_name_pattern
        self.record_type = (record_type or 'TXT').upper()
        self.allow_replace = bool(allow_replace)
        self.allow_delete = bool(allow_delete)


def _rrset_changetype(rrset: dict) -> str:
    return (rrset.get('changetype') or '').upper()


def evaluate_patch(rules: Iterable[AclRule], zone_id: str,
                   body: dict) -> Tuple[bool, str]:
    """Decide whether a PATCH ``rrsets[]`` body is allowed.

    Returns ``(True, '')`` if every rrset in the body is permitted by at
    least one rule for the matching zone, else ``(False, reason)``.
    """
    if not isinstance(body, dict):
        return False, 'request body is not a JSON object'
    rrsets = body.get('rrsets')
    if not isinstance(rrsets, list) or not rrsets:
        return False, 'rrsets[] missing or empty'

    zone = _normalise(zone_id)
    rules = [r for r in rules if r.domain_name == zone]
    if not rules:
        return False, 'apikey has no rrset acl rules for zone {0}'.format(zone)

    for rrset in rrsets:
        if not isinstance(rrset, dict):
            return False, 'rrset entry is not an object'
        name = rrset.get('name', '')
        rtype = (rrset.get('type') or '').upper()
        change = _rrset_changetype(rrset)
        if change not in ('REPLACE', 'DELETE'):
            return False, 'changetype {0!r} not permitted for scoped key'.format(
                change or '<missing>')

        ok = False
        for rule in rules:
            if rule.record_type != rtype:
                continue
            if not match_pattern(rule.record_name_pattern, name):
                continue
            if change == 'REPLACE' and not rule.allow_replace:
                continue
            if change == 'DELETE' and not rule.allow_delete:
                continue
            ok = True
            break
        if not ok:
            return False, (
                'rrset {0}/{1} ({2}) not permitted by any acl rule'
            ).format(name, rtype, change)
    return True, ''


def rules_from_apikey(apikey) -> list:
    """Adapt an :class:`ApiKey` ORM object to a list of :class:`AclRule`."""
    out = []
    for row in getattr(apikey, 'rrset_acls', None) or []:
        domain_name = row.domain.name if row.domain is not None else ''
        out.append(AclRule(
            domain_name=domain_name,
            record_name_pattern=row.record_name_pattern,
            record_type=row.record_type,
            allow_replace=row.allow_replace,
            allow_delete=row.allow_delete,
        ))
    return out


def validate_pattern_syntax(pattern: str) -> Tuple[bool, str]:
    """Return (ok, reason) for a pattern submitted via the mint endpoint."""
    if not pattern or not isinstance(pattern, str):
        return False, 'pattern is empty'
    if len(pattern) > 255:
        return False, 'pattern too long'
    n = _normalise(pattern)
    if not n:
        return False, 'pattern is empty'
    labels = n.split('.')
    star_count = 0
    for label in labels:
        if not label:
            return False, 'empty label in pattern'
        if label == '*':
            star_count += 1
            continue
        if '*' in label:
            return False, 'wildcard `*` only allowed as a full label'
        # Permissive label charset (DNS labels + `_` for ACME).
        for ch in label:
            if not (ch.isalnum() or ch in '-_'):
                return False, 'invalid character {0!r} in pattern'.format(ch)
    if star_count > 1:
        return False, 'at most one `*` label allowed'
    return True, ''


def pattern_within_zone(pattern: str, zone_name: str) -> bool:
    """Pattern must be the zone apex or a subdomain of the zone."""
    p = _normalise(pattern)
    z = _normalise(zone_name)
    return p == z or p.endswith('.' + z)
