# Reporting

This file contains the rules behind the numbers finance and merchandising see: which reports
exist, why they lag a day, why yesterday's numbers can change, and which number wins when two
reports disagree. Ask here for why questions about the daily sales report, stock counts not
matching, and restated figures.

Related: engineering/reconciliation.md, product/inventory.md
Owner: finance

## Index

1. Which reports exist — the daily sales, stock and margin reports, who reads them and when
2. Why numbers lag a day — why every report shows yesterday and never today, and why that is a promise not a limitation
3. When yesterday changes — why a figure can be restated for up to 3 days and how we flag it
4. Which number wins — the rule for disagreements between the storefront, the warehouse count and the report

## Which reports exist

Daily sales (finance, 08:00), daily stock (merchandising, 08:00, this is where the Book A
count is checked), monthly margin (commercial, 3rd working day). All are produced by the
nightly reconciliation (engineering/reconciliation.md).

## Why numbers lag a day

Reports show complete days only. Refunds, cancellations and warehouse corrections arrive
through the day, so a live number would be wrong by evening. We promised finance a number
that does not move once the day is closed, which is worth more than a number that is fresh.

## When yesterday changes

Warehouse corrections can arrive up to 3 days late, so a closed day may be restated until
then. A restated day is marked in the report with the previous value; nothing is overwritten
silently. After 3 days a correction becomes a manual adjustment with a reason.

## Which number wins

Warehouse physical count beats the storefront's stock number, which beats the report. If the
report says Book A has 22 copies and the warehouse count says 18, the rule has been broken
and merchandising is told, regardless of what the storefront shows.
