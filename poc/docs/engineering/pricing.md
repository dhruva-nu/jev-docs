# Pricing

This file contains the price calculation service and its data: the quote endpoint, the
pipeline that applies discounts, founders discount, price match and rounding in code, and the
tables that store discounts. Ask here for how questions about where a price is computed,
the discount tables, and how the founders discount is applied in code.

Related: product/pricing.md
Owner: checkout team

## Index

1. Quote API — the /quote endpoint, its request and response, and how the storefront and checkout call it
2. Price pipeline — the ordered steps in price_pipeline.py and where each rule is implemented
3. Discount tables — the discounts and discount_redemptions tables and their constraints
4. Founders discount in code — where the hard-coded 7% lives, why it is a constant not a discount row, and the test that guards it

## Quote API

`POST /quote` takes `{items: [{isbn, qty}], customer_id?, discount_code?, price_match?}` and
returns `{lines: [{isbn, list, discount, founders, match, final}], total}`. Checkout calls it
again at payment time; the storefront result is advisory only.

## Price pipeline

`price_pipeline.py` runs `list_price -> best_discount -> founders -> price_match -> round_99`.
Each step is a pure function of the previous line; the order is asserted by
`test_pipeline_order`. `round_99(x)` returns the largest price ending in .99 that is not above `x`, so rounding
is always down and always in the customer's favour.

## Discount tables

`discounts(code pk, percent, starts_at, ends_at not null, created_by)` — `ends_at` is NOT NULL
by design. `discount_redemptions(order_id, code)` has a unique constraint per order, which is
how "no stacking" is enforced.

## Founders discount in code

`FOUNDERS_DISCOUNT = Decimal("0.07")` in `pricing/constants.py`. It is not a `discounts` row
because it has no end date and the table forbids that. `test_founders_discount_present` fails
the build if the constant is removed, so removal is a deliberate change that needs a product
sign-off comment in the PR.
