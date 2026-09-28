# Recommendations

This file contains how the recommendation model is built and served: its inputs, the
post-model exclusion filter, the serving thresholds, the nightly retraining, and drift
monitoring. Ask here for how questions about model features, where Book B is filtered
out, why a score threshold is set, retraining schedules, and model monitoring.

Related: product/recommendations.md
Owner: ML team

## Index

1. Model inputs — the features the model uses and the ones it is forbidden to use
2. Exclusion filter — the deterministic post-model filter that removes Book B, bought, out-of-stock and legal-flagged titles
3. Serving and thresholds — the /recommendations endpoint, the minimum score, and the staff-picks fallback
4. Retraining — the nightly training job, its data window, and how a new model is promoted
5. Drift and monitoring — the dashboards and alerts that show the model degrading and what to do

## Model inputs

Purchase history (last 24 months), browsing sessions (last 90 days), author follows, city.
Forbidden: any Book B interaction (removed at ingestion), margin, and any demographic field.

## Exclusion filter

`recs/filter.py::exclude()` runs after scoring and before response. It drops ISBNs in
`anonymised_isbns`, ISBNs in the customer's orders, ISBNs with `stock.available = 0`, ISBNs in
`legal_flags`, and dismissals from the last 90 days read live from `rec_dismissals`. It is
deterministic and unit-tested; the model is never relied upon to learn these rules.

## Serving and thresholds

`GET /recommendations?customer_id=` returns up to 8 titles with `reason_code`. Titles scoring
below 0.2 are dropped. If fewer than 3 remain, or the customer has no history, the response is
the `staff_picks` list with `reason_code = staff_pick`.

## Retraining

`train_recs` runs nightly at 02:00 on the last 24 months of data. A new model is promoted only
if offline add-to-basket rate is within 1% of the current model or better; otherwise the job
keeps the old model and posts to `#ml-alerts`.

## Drift and monitoring

The "Recs health" dashboard tracks click-through, add-to-basket from recommendations and share
of staff-pick fallbacks. An alert fires if fallback share doubles day on day, which usually
means the feature store is stale. Runbook: check the `features_daily` job first.
