# Permissions

This file contains who is allowed to do what, across every part of the bookstore: the roles
we have, what each may see or change, and the rules that apply to everyone. Ask here for
why questions about roles, why a staff member cannot see something, why a customer cannot do
something, and what an admin must never be able to do.

Related: engineering/permissions.md, product/inventory.md, product/pricing.md
Owner: security + product

## Index

1. Roles — the roles that exist (customer, store staff, store manager, commercial, support, admin) and one line on each
2. Who may see customer data — the rules on viewing orders and personal data, including that nobody can see who bought Book B
3. Who may change prices and discounts — which roles may create, apply or override a discount or price match
4. Admin limits — the things an admin is deliberately not allowed to do alone, and why
5. Audit promise — what we promise about every privileged action being recorded

## Roles

Customer: buys and reads. Store staff: fulfils orders, applies existing discounts. Store
manager: staff plus price match and reserved copies. Commercial: creates discounts, sets
prices. Support: views orders and issues refunds. Admin: manages roles and configuration.

## Who may see customer data

Support and store managers may see a customer's orders when handling that customer's request.
Nobody, including admins, can see who bought Book B; the data does not exist after fulfilment
(see product/inventory.md). Exports of customer data need two people from different roles.

## Who may change prices and discounts

Only commercial creates discounts or changes list prices. Store managers apply price match.
Store staff apply an existing discount code. Nobody may remove the 7% founders discount
without commercial and founder sign-off (see product/pricing.md).

## Admin limits

An admin cannot grant themselves commercial or support rights; a second admin must do it.
An admin cannot read customer data or change prices. This exists so that a compromised admin
account cannot leak data or move money.

## Audit promise

Every action by a non-customer role is recorded with who, what, when and from where, and kept
for seven years. Customers can ask what was done on their account and we will tell them.
