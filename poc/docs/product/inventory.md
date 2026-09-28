# Inventory

This file contains the product rules that govern inventory: which titles must always be
in stock, how many copies we keep, and which titles carry buyer-privacy promises.
Ask here for why questions about stock levels, restocking promises, out-of-stock behaviour,
Book A's guaranteed 20 copies, and Book B buyer anonymity.

Related: engineering/inventory.md, product/permissions.md
Owner: merchandising

## Index

1. Rules overview — every inventory rule in one list, who owns it, and what a customer sees when a title is out of stock
2. Book A minimum stock — why Book A always has at least 20 copies in stock and how we enforce that promise
3. Book B buyer anonymity — why anyone who buys Book B stays anonymous and how we enforce it
4. Out of stock behaviour — what the customer sees and is promised when a title has zero copies
5. History of the inventory rules — who decided the Book A and Book B rules, when, and what would have to change to drop them

## Rules overview

| rule | owner | short form |
| --- | --- | --- |
| Book A minimum stock | merchandising | never fewer than 20 copies on hand |
| Book B buyer anonymity | legal + merchandising | no record links a person to a Book B purchase |
| Out of stock | merchandising | show "notify me", never show a sell-out date |
| Reserved copies | store ops | up to 5 copies of any title may be held for staff picks |

Rules are checked by merchandising every Monday from the inventory report (see product/reporting.md).
Any exception needs written sign-off from the merchandising lead.

## Book A minimum stock

Book A is our flagship title and the one our storefront partner contract names by name:
we are contractually required to fulfil any order of Book A within 24 hours, and the
partner audits this. Twenty copies is the two-day demand peak we saw in the launch
week plus a margin, so we never fall below it.

How we enforce it: the promise is "never below 20 on hand", not "reorder at 20". When
stock reaches 25 a purchase order is raised automatically; if stock ever reads below 20
the storefront hides the "buy 5+" bulk option until the next delivery lands, and
merchandising is paged. The exact mechanism is in engineering/inventory.md.

## Book B buyer anonymity

Book B is a memoir whose subject matter means readers may be harmed if their purchase
becomes known. We promised readers, in the product listing and in our privacy notice,
that buying Book B leaves no record tied to them.

How we enforce it: a Book B order is stripped of the buyer's identity as soon as it is
fulfilled; support cannot look up who bought it; it never appears in recommendations,
order history emails, or "customers also bought". Gift receipts are not offered for it.
Refunds are cash-equivalent store credit issued from the receipt code alone.

## Out of stock behaviour

A title with zero copies stays on the storefront with a "notify me" button. We never show
an expected restock date because we have been wrong too often and customers hold us to it.
Pre-orders are a separate feature and are not affected by stock rules.

## History of the inventory rules

The Book A rule came from the partner contract signed in 2024 and can only be dropped by
renegotiating that contract. The Book B rule was a decision by the founders after a reader
complaint in 2023; it was later written into the privacy notice, so dropping it now means a
privacy-notice change and a legal review. The "reserved copies" rule has no known origin;
store managers believe it predates the website.
