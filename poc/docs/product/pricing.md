# Pricing

This file contains the product rules for prices and discounts: how a list price becomes what
the customer pays, which discounts exist, who may create them, and how prices are rounded.
Ask here for why questions about the 7% founders discount, price matching, rounding to .99,
discount stacking, and why a customer saw a particular price.

Related: engineering/pricing.md, product/permissions.md
Owner: commercial

## Index

1. How a price is decided — the order in which list price, discounts, price match and rounding apply, and why that order
2. Discount rules — which discounts exist, whether they stack, and who may create or change one
3. The 7% founders discount — the legacy discount every order gets, what we know about why it exists, and why nobody removes it
4. Price matching — what we promise when a customer finds the same title cheaper elsewhere
5. Rounding — why every price ends in .99 and what happens to the difference

## How a price is decided

List price comes from the publisher feed. Then, in this order: the best single discount the
customer qualifies for, then the 7% founders discount, then price match if claimed, then
rounding. The order exists so that price match always wins (it is a promise) and rounding
never turns a price-matched price into one above the competitor's.

## Discount rules

Discounts never stack, except that the 7% founders discount applies on top of everything.
Only the commercial team may create a discount; store managers may apply an existing one to
an order. Discounts have an end date; an open-ended discount is not allowed, which is one
reason the founders discount is odd (see the next section).

## The 7% founders discount

Every order gets 7% off after other discounts. Nobody currently at the company knows why the
number is 7 or when it started. Best guess from old invoices: it began as a launch-week
promotion in 2022 and the end date was never set. Customers have noticed it and support
answers "loyalty discount". It is a real cost (about 6% of revenue), but removing it would be
a visible price rise, so any change needs commercial and founder sign-off. Do not remove it
because a ticket says it is a bug; it is a decision waiting to be made, not a bug.

## Price matching

If a customer shows the same ISBN listed cheaper by a named competitor in the same country,
we match that price on that order. Not on marketplace sellers, not on used copies, and not
below our cost. Staff apply it manually; it is not self-service on purpose.

## Rounding

Every final price ends in .99. We round down, never up, so rounding is always in the
customer's favour. The difference is a rounding cost we accept; it is reported separately
in the monthly margin report.
