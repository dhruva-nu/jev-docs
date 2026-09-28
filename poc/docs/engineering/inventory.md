# Inventory

This file contains the APIs, tables and service rules for inventory: the stock endpoints,
the stock and purchase-order tables, the Book A restock job, and the Book B order
anonymisation hook. Ask here for how questions: which endpoint, which table, which job,
and how an inventory rule is enforced in code.

Related: product/inventory.md
Owner: platform team

## Index

1. API contracts — the /stock and /purchase-orders endpoints, their payloads, and error codes
2. Tables — the stock, purchase_orders and stock_events tables, their columns and invariants
3. Book A restock job — the cron job that keeps Book A at 20 or more copies: schedule, threshold, purchase order, paging
4. Book B anonymisation — the fulfilment hook that strips buyer identity from Book B orders and exactly what it deletes
5. Failure modes — what a broken restock job or a leaked Book B record looks like, and how to fix each

## API contracts

`GET /stock/{isbn}` returns `{isbn, on_hand, reserved, available, updated_at}`.
`POST /stock/{isbn}/adjust` takes `{delta, reason}`; `reason` is required and one of
`sale`, `refund`, `delivery`, `correction`. Returns 409 if the result would go negative.
`POST /purchase-orders` takes `{isbn, quantity, supplier_id}` and returns the order id.
Only the `inventory-service` and `restock-job` service accounts may call it.

## Tables

`stock(isbn pk, on_hand int not null check (on_hand >= 0), reserved int not null default 0, updated_at)`.
`purchase_orders(id pk, isbn, quantity, supplier_id, status enum(open, sent, received, cancelled), created_at)`.
`stock_events(id pk, isbn, delta, reason, actor, created_at)` is append-only; `stock.on_hand`
must always equal the sum of `stock_events.delta` for that isbn, and reconciliation checks it nightly.

## Book A restock job

`restock_book_a` runs every 10 minutes (`*/10 * * * *`) in the jobs worker. It reads
`stock.on_hand` for Book A's ISBN. At `on_hand <= 25` with no open purchase order it calls
`POST /purchase-orders` for 30 copies. At `on_hand < 20` it sets the storefront flag
`book_a_bulk_disabled=true` and pages `#merch-oncall` through PagerDuty. The flag is cleared by
the `delivery` stock adjustment handler once `on_hand >= 20`. Thresholds live in
`config/inventory.yaml` under `book_a`.

## Book B anonymisation

The `order.fulfilled` event handler checks the ISBN against `config/inventory.yaml:anonymised_isbns`.
For a match it replaces `orders.customer_id` with NULL, deletes the shipping address row,
replaces the payment reference with a random receipt code, and writes no `stock_events.actor`.
Recommendation and email pipelines also filter on `anonymised_isbns` at read time, as a
second line of defence. A test in `tests/test_anonymise.py` asserts no row references the buyer.

## Failure modes

Restock job not running: Book A `on_hand` falls with no open purchase order; the job's
heartbeat alert fires after 30 minutes. Fix by restarting the jobs worker; the next run
catches up. Leaked Book B record: any query joining `orders` to `customers` for an anonymised
ISBN returning rows. Treat as a privacy incident: page security, do not delete evidence,
follow engineering/on-call.md severity 1.
