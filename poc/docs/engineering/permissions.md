# Permissions

This file contains how roles and access are implemented: the role and grant tables, the
authorization middleware every endpoint goes through, the two-person rule, and the audit log.
Ask here for how questions about RBAC tables, where a permission check happens, how
approvals are enforced, and where audit records are stored.

Related: product/permissions.md
Owner: security team

## Index

1. Role tables — the roles, grants and role_assignments tables and their constraints
2. Authorization middleware — the require() decorator, how a request is checked, and the deny-by-default rule
3. Two-person rule — how self-grants and customer-data exports require a second approver in code
4. Audit log — the audit_events table, what is written on every privileged action, and retention

## Role tables

`roles(name pk)`, `grants(role, permission)`, `role_assignments(user_id, role, granted_by)`.
A check constraint forbids `granted_by = user_id`.

## Authorization middleware

Every handler is decorated with `@require("permission.name")`. A handler without one fails
startup. Permissions are resolved per request from `role_assignments` joined to `grants`.

## Two-person rule

`approvals(id, action, requested_by, approved_by)` with `approved_by <> requested_by`. Exports and
role grants create an approval and run only once approved by a user with a different role.

## Audit log

`audit_events(actor, action, target, ip, at)` is written by the middleware for every
non-customer request, streamed to cold storage and kept seven years.
