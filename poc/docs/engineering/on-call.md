# On-call

This file contains how engineering runs incidents: who is paged and when, the severity
ladder, the rollback runbook, and the postmortem process. Ask here for how questions about
getting paged, declaring an incident, rolling back a deploy, and writing a postmortem.

Related: product/reliability.md
Owner: engineering managers

## Index

1. Paging — the rotations, what pages whom, and the acknowledgement timeouts
2. Severity ladder — how to decide severity 1, 2 or 3 and what each one triggers
3. Rollback runbook — the steps to roll the storefront back to the previous release
4. Postmortem process — the template, the deadline and the blameless review meeting

## Paging

Two rotations: `platform` (storefront, checkout, jobs) and `mobile`. PagerDuty pages primary,
escalates to secondary after 10 minutes unacknowledged, then to the engineering manager.

## Severity ladder

Sev 1: checkout down or a privacy breach (including any Book B leak). Sev 2: checkout degraded
or a core job failing. Sev 3: anything else customer-visible. Sev 1 and 2 need an incident
commander and trigger the status page policy in product/reliability.md.

## Rollback runbook

Run `deploy rollback storefront --to previous`, confirm the synthetic checkout goes green, then
announce in `#incidents`. Database migrations are forward-only; if the bad release ran one,
roll forward with a fix instead.

## Postmortem process

Draft within 5 working days using `templates/postmortem.md`, review in the weekly blameless
meeting. Sev 1 postmortems become the public write-up edited by the support lead.
