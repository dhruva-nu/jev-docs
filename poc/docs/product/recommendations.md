# Recommendations

This file contains the product rules for the "you might like" recommendations: what may and
may never be recommended, what a new customer sees, and what we promise about explaining a
recommendation. Ask here for why questions about why a customer was recommended a title, why
Book B never appears, cold-start behaviour, and what "why this?" shows.

Related: engineering/recommendations.md, product/inventory.md
Owner: growth

## Index

1. What recommendations are for — the goal of the feature and the metric we optimise, and what we refuse to optimise
2. Never-recommend rules — titles and situations where a recommendation must never appear, including Book B, and how we enforce that
3. New customers and cold start — what a customer with no history sees and why it is a curated list, not a model
4. Explaining a recommendation — what the "why this?" link promises and what it must never reveal about other customers
5. When the model is wrong — how a customer or support dismisses a recommendation and what we promise happens next

## What recommendations are for

The feature exists to help a reader find their next book, measured by add-to-basket from a
recommendation within the session. We do not optimise for margin: a recommendation must never
be chosen because it is more profitable. That was a deliberate decision in 2024 after a test
that raised margin and lowered repeat visits.

## Never-recommend rules

A recommendation must never show: Book B (buyer anonymity, see product/inventory.md); any
title the customer has already bought; any title out of stock; any title flagged by legal.
These are hard rules, not preferences: the model is not trusted to learn them, they are
enforced as a filter after the model runs, so even a broken model cannot break the promise.

## New customers and cold start

A customer with no purchase or browsing history sees the curated "staff picks" list, chosen
weekly by merchandising, not a model output. We do this because model guesses for unknown
customers were measurably worse than a human list, and because a wrong first recommendation
costs more trust than no recommendation.

## Explaining a recommendation

Every recommendation has a "why this?" link. It shows one of a fixed set of reasons: "because
you bought X", "popular in your city", "staff pick", "new from an author you follow". It never
shows or implies what other individual customers bought, and it is never generated free-form.

## When the model is wrong

A customer can dismiss a recommendation; a dismissed title is not shown again for 90 days.
Support can dismiss on a customer's behalf. We promise the dismissal takes effect immediately
on the next page load, which is why dismissals are not left to the nightly retrain.
