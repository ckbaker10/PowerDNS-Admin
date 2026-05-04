from flask import current_app

from .base import db


class ApiKeyRrsetAcl(db.Model):
    """Restricts an ApiKey to a specific (record_name_pattern, record_type)
    within a single domain. When at least one row exists for an ApiKey, the
    key is treated as record-scoped: the key may only PATCH rrsets that
    match one of its rows, and may not perform zone-level write operations
    (POST/PUT/DELETE on the zone object).

    Pattern grammar (intentionally narrow, no regex):
      - exact FQDN, e.g. ``_acme-challenge.host.example.com.``
      - one ``*`` allowed, only as a single full label, e.g.
        ``_acme-challenge.*.example.com.`` — matches exactly one label.
    Trailing dot is optional and normalised on compare.
    """
    __tablename__ = "apikey_rrset_acl"

    id = db.Column(db.Integer, primary_key=True)
    apikey_id = db.Column(db.Integer,
                          db.ForeignKey('apikey.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    domain_id = db.Column(db.Integer,
                          db.ForeignKey('domain.id', ondelete='CASCADE'),
                          nullable=False)
    record_name_pattern = db.Column(db.String(255), nullable=False)
    record_type = db.Column(db.String(10), nullable=False, default='TXT')
    allow_replace = db.Column(db.Boolean, nullable=False, default=True)
    allow_delete = db.Column(db.Boolean, nullable=False, default=True)

    apikey = db.relationship('ApiKey', back_populates='rrset_acls')
    domain = db.relationship('Domain')

    def __init__(self, apikey_id=None, domain_id=None,
                 record_name_pattern=None, record_type='TXT',
                 allow_replace=True, allow_delete=True):
        self.apikey_id = apikey_id
        self.domain_id = domain_id
        self.record_name_pattern = record_name_pattern
        self.record_type = (record_type or 'TXT').upper()
        self.allow_replace = bool(allow_replace)
        self.allow_delete = bool(allow_delete)

    def __repr__(self):
        return (
            "<ApiKeyRrsetAcl apikey={0} domain={1} {2} {3} "
            "replace={4} delete={5}>"
        ).format(self.apikey_id, self.domain_id,
                 self.record_name_pattern, self.record_type,
                 self.allow_replace, self.allow_delete)

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(
                'Cannot insert apikey_rrset_acl row. Error: {0}'.format(e))
            db.session.rollback()
            raise
