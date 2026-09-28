# Reconciliation

This file contains the nightly reconciliation pipeline that produces every report: its
schedule and steps, how reruns and late warehouse corrections are handled, how a missed night
is backfilled, and what failures look like. Ask here for how questions about the nightly job,
rerunning a day, restating figures in code, and fixing a failed run.

Related: product/reporting.md, engineering/inventory.md
Owner: data team

## Index

1. Schedule and steps — when the nightly job runs and the order of its extract, check, and publish steps
2. Idempotency and reruns — why rerunning a day is safe and how to rerun one
3. Late corrections — how warehouse corrections up to 3 days late restate a closed day
4. Backfill and failure — what a failed night looks like, the alerts, and how to backfill

## Schedule and steps

`reconcile_daily` runs at 01:30 for the previous day: extract orders and stock events, check
`stock.on_hand` against the sum of `stock_events`, compare with the warehouse count feed,
build the three reports, publish at 07:30.

## Idempotency and reruns

Every step writes to a partition keyed by date and replaces it whole, so a rerun gives the same
result. Rerun with `reconcile_daily --date 2026-09-01`.

## Late corrections

Each run also reprocesses the three previous days. A changed figure writes a `restatements` row
with old and new values, which the report renders as a flag.

## Backfill and failure

A failed run pages the data rotation at 07:00 if reports are not published. Backfill by running
`reconcile_daily --from <date> --to <date>`; runs are ordered oldest first.
