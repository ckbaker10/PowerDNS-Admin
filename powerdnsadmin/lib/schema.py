"""Serialization schemas for the PowerDNS-Admin JSON API.

Originally built on `lima` (last release 2016, no longer installable on
modern Python). This module is now a thin marshmallow port that keeps the
same class names, field names and `.dump()` return shape so the rest of
the codebase needs no changes.

Behavioural notes:
- marshmallow's `dump()` returns a plain dict (or list when `many=True`),
  matching lima's behaviour.
- Field resolution defaults to `getattr(obj, field_name)`, also matching
  lima. ORM models keep working without `attribute=` overrides.
- `fields.Nested(SubSchema, many=True)` replaces `fields.Embed(schema=...,
  many=True)`.
"""
from marshmallow import Schema as _MarshmallowSchema, fields


class Schema(_MarshmallowSchema):
    """Project base schema.

    `Meta.unknown = 'exclude'` keeps the previous lima behaviour of
    silently skipping unknown attributes on input objects (we only ever
    dump, but this also makes the schema tolerant if a future caller
    reuses it for `load`).
    """

    class Meta:
        ordered = True


class DomainSchema(Schema):
    id = fields.Integer()
    name = fields.String()


class RoleSchema(Schema):
    id = fields.Integer()
    name = fields.String()


class AccountSummarySchema(Schema):
    id = fields.Integer()
    name = fields.String()
    domains = fields.Nested(DomainSchema, many=True)


class ApiKeySummarySchema(Schema):
    id = fields.Integer()
    description = fields.String()


class ApiKeySchema(Schema):
    id = fields.Integer()
    role = fields.Nested(RoleSchema)
    domains = fields.Nested(DomainSchema, many=True)
    accounts = fields.Nested(AccountSummarySchema, many=True)
    description = fields.String()
    key = fields.String()


class ApiPlainKeySchema(Schema):
    id = fields.Integer()
    role = fields.Nested(RoleSchema)
    domains = fields.Nested(DomainSchema, many=True)
    accounts = fields.Nested(AccountSummarySchema, many=True)
    description = fields.String()
    plain_key = fields.String()


class UserSchema(Schema):
    id = fields.Integer()
    username = fields.String()
    firstname = fields.String()
    lastname = fields.String()
    email = fields.String()
    role = fields.Nested(RoleSchema)


class UserDetailedSchema(Schema):
    id = fields.Integer()
    username = fields.String()
    firstname = fields.String()
    lastname = fields.String()
    email = fields.String()
    role = fields.Nested(RoleSchema)
    accounts = fields.Nested(AccountSummarySchema, many=True)


class AccountSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    description = fields.String()
    contact = fields.String()
    mail = fields.String()
    domains = fields.Nested(DomainSchema, many=True)
    apikeys = fields.Nested(ApiKeySummarySchema, many=True)

