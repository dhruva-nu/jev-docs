# Reliability

This file contains what we promise customers and partners about uptime and incidents: the
availability target, what we say publicly during an outage, when we credit partners, and
who may speak for us. Ask here for why questions about the SLA, the status page, outage
communication, and partner credits.

Related: engineering/on-call.md
Owner: support lead

## Index

1. The availability promise — the uptime target, what counts as down, and why it is set where it is
2. Status page policy — when we post, what we say, and who is allowed to post
3. Partner credits — when a partner is owed a credit for an outage and how much
4. Postmortems customers see — which incidents get a public write-up and what it must contain

## The availability promise

The storefront target is 99.9% monthly, measured as the share of minutes in which checkout
succeeds for a synthetic order. Browsing being down counts; the mobile app being down does
not count against the storefront number. The target is written into the partner contract.

## Status page policy

We post within 15 minutes of an incident being declared severity 1 or 2, in plain language,
without blame or technical detail. Only the incident commander or the support lead may post.
Updates every 30 minutes until resolved, then a final "resolved" post.

## Partner credits

A partner is owed a credit when monthly availability falls below 99.9%: 5% of that month's
fee per 0.1% shortfall, capped at 25%. Credits are calculated by finance from the incident
log, not claimed by partners.

## Postmortems customers see

Any severity 1 incident gets a public postmortem within 10 working days. It must state what
happened, how long it lasted, what customers experienced, and what we changed. It never names
individuals.
