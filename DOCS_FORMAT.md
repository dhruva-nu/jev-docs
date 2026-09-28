# The jev-docs format

How to write documentation so that a router built on Jev can take any question,
decide whether it is a product or an engineering question, find the one file that
covers it, and point at the one section that answers it.

The router never reads section bodies. It reads three things, in order:

1. the **domain** descriptions (`product`, `engineering`),
2. each file's **summary** (the first 2–5 lines),
3. the chosen file's **index** (one line per section).

So the format exists to make those three things carry the signal. The bodies are
the payload that gets handed back once the route is known.

---

## 1. Tree layout

```
docs/
  product/              "why": rules, policies, promises, decisions, user-facing behaviour
    README.md           2–5 lines describing what belongs in this domain  (optional, has a default)
    inventory.md
    pricing.md
    ...
  engineering/          "how": APIs, tables, services, jobs, code paths, runbooks, enforcement mechanics
    README.md
    inventory.md
    pricing.md
    reconciliation.md
    ...
```

- Exactly two levels: `<domain>/<topic>.md`. No subfolders. If you want a subfolder,
  you want a new topic file (see §4).
- File names are lower-kebab-case nouns: `inventory.md`, `offline-sync.md`.
- A topic that exists in both domains uses the **same file name** in both. These are
  "twins" and must link to each other with a `Related:` line. Twins are not required:
  `product/reporting.md` may pair with `engineering/reconciliation.md` when the two
  audiences genuinely name the thing differently.

## 2. File anatomy

```markdown
# Inventory

This file contains the product rules that govern inventory: which titles must
always be in stock, and which titles carry buyer-privacy constraints. Ask here for
"why" questions about stock levels, restocking promises and buyer anonymity.

Related: engineering/inventory.md
Owner: merchandising

## Index

1. Rules overview — every inventory rule in one list, and who owns each
2. Book A minimum stock — why Book A always has 20 copies and how we enforce it
3. Book B buyer anonymity — why Book B buyers stay anonymous and how we enforce it

## Rules overview
...body...

## Book A minimum stock
...body...

## Book B buyer anonymity
...body...
```

| part | rule | what the router does with it |
| --- | --- | --- |
| `# Title` | one H1, the topic name | label shown in routes |
| summary | 2–5 plain lines directly under the H1 | the **only** text used to pick this file over its siblings |
| `Related:` / `Owner:` | optional metadata lines after the summary | `Related:` is followed when the answer spans domains |
| `## Index` | numbered list, one entry per section: `N. Title — blurb` | the **only** text used to pick a section |
| `## Section` | one H2 per index entry, same title, in the same order | returned as the answer payload |

Hard rules the linter enforces:

- Summary is 2–5 lines, not counting blank and metadata lines.
- Index has 3–12 entries. Fewer: merge into a neighbour topic. More: split the topic.
- Every index entry has a blurb after ` — ` (em dash) or ` - `.
- Every index entry matches an H2 by title; no H2 is missing from the index; order matches.
- No H3 or deeper inside a section that the router should be able to land on.
  If you need H3s, the section is too big: promote them to sections or split the file.

## 3. Writing the summary and blurbs for a router

The summary and the blurbs are read by a model that is choosing between siblings.
Write them to be **distinguishable**, not pretty.

- Say what **questions** the file answers, not what the topic "is":
  bad: "Inventory management." good: "Ask here for why stock levels are what they
  are, which titles are always kept in stock, and what buyers of restricted titles are
  promised."
- Use the words a reader would type. If people say "out of stock", say "out of stock",
  not "availability shortfall".
- Name the concrete entities: "Book A", "the 7% founders discount", "the nightly
  reconciliation job". Proper nouns are the strongest routing signal there is.
- A blurb states what the section answers: "why Book A always has 20 copies and how we
  enforce it". Not "Book A" alone.
- Do not repeat the summary in every blurb. Each blurb should be the reason to pick
  *that* section over its siblings.
- Put the "how we enforce it" in the product file too, in product words (a promise,
  a rule, a check someone does), and leave the mechanism (a cron job, a trigger) to
  the engineering twin.

## 4. What is a topic (one file)

A topic is the noun a person would say when asked "what area is this question
about?" It is an area of responsibility, not a feature, a ticket, or a release.

Tests, in order:

1. **The one-noun test.** Can the summary name the topic with one noun phrase
   (`inventory`, `pricing`, `offline sync`)? If the summary needs "and" between two
   unrelated nouns, split.
2. **The persona test.** Would the same person be asked about all of it? If half of
   the questions go to merchandising and half to the fraud team, split.
3. **The index-size test.** 3–12 sections. Above 12, split along the biggest seam.
   Below 3, merge into the topic that shares the most vocabulary.
4. **The sibling test.** Read the summaries of all files in the domain side by side.
   If two could plausibly answer the same question, either merge them or rewrite the
   summaries until the boundary is obvious.
5. **The cross-cutting test.** Permissions, privacy, audit, pricing, feature flags,
   and similar concerns touch many topics. They get their **own** file. The topics
   they touch mention them in a `Related:` line and, where a rule bites, in a section
   blurb ("Book B buyer anonymity" lives in inventory *and* privacy points at it).
   The router only finds one file per hop, so the cross-cutting file must be
   findable by its own summary, and the touching file must be findable by its blurb.

## 5. What is a section (one index entry)

A section answers one **family** of questions with one shape. Typical shapes:

| shape | section answers | domain it usually lives in |
| --- | --- | --- |
| rule | what is the rule, why does it exist, who decided, what happens when broken | product |
| contract | what is the interface: endpoints, payloads, tables, columns, events | engineering |
| mechanism | how is a rule actually enforced, where in the code, which job | engineering |
| lifecycle | what happens over time: schedules, states, retries, expiry | either |
| failure | what breaks, what it looks like, what we do, who we tell | either |
| history | why it is the way it is, the decision that nobody remembers | product (yes, even for code) |
| glossary | terms and numbers people misuse | either |

A section is too big when its blurb needs "and" between two shapes ("the rule and how
we enforce it" is fine as *one* product section; "the API and the tables and the
job" is three engineering sections).

## 6. Product versus engineering

| | product | engineering |
| --- | --- | --- |
| question words | why, what is the rule, what do we promise, who decided, what does the user see, is it allowed | how, where, which table, which endpoint, which job, what happens in the code, how do I run it |
| audience | PM, support, sales, compliance, a new engineer asking "why" | engineers, on-call, data, anyone asking "how" |
| enforcement | described as a promise or a check ("we never let it fall below 20") | described as a mechanism ("`restock_book_a` runs every 10 minutes and inserts a PO") |

When a reader's question needs both ("why do we have 20 copies *and* how is that
enforced?"), the router returns the primary route and follows `Related:` to the
twin. Write both files so that each stands alone for its own audience.

## 7. Fitting every kind of software into this shape

Web APIs are easy: contracts, tables, service rules. The format has to fit the rest.
The trick is always the same: **the topic is the responsibility, the sections are the
question shapes from §5, and the summary says which questions land here.**

| kind of software | what makes it hard | how to slice it |
| --- | --- | --- |
| **Batch / data pipeline** (nightly reconciliation) | no request/response; correctness is about time, ordering and reruns | product: `reporting.md` (what numbers people see, why they lag). engineering: `reconciliation.md` with lifecycle (schedule, steps), idempotency (rerun rules), failure (what a bad night looks like, how to backfill) |
| **ML / recommendation model** | non-deterministic; "why did it do that" has no single code path | product: `recommendations.md` with rules (what may never be shown), explainability promise, cold-start behaviour. engineering: model inputs, exclusion enforcement (which is deterministic and *must* be documented as a mechanism), thresholds, retraining cadence, drift monitoring |
| **Mobile / offline sync** | behaviour is a protocol between devices, not a place in code | product: what a user can do offline, what wins on conflict, in user words. engineering: sync protocol, conflict resolution algorithm, queue and retry, versioning |
| **Operational process** (on-call, incidents) | it is people and habits, not code | product: `reliability.md`: what we promise customers, what we say on the status page. engineering: `on-call.md`: paging, severity ladder, rollback runbook, postmortem rule. Runbooks are sections with a lifecycle shape |
| **Cross-cutting policy** (permissions, privacy, audit) | touches every topic | its own file per §4.5; every touched topic points back with `Related:` and a blurb |
| **Tribal knowledge / legacy behaviour** ("why is there a 7% discount?") | nobody wrote it down because nobody knows | a **history** section in the product file, written honestly: "we do not know; best guess; do not remove without checking X". An honest "unknown" is routable; silence is not |
| **Third-party integration** (payments provider) | half the behaviour is theirs | product: what we promise regardless of the provider. engineering: our adapter, their quirks we work around, what to do when they are down |
| **Library / CLI / SDK** | no users, only callers | product: the guarantees (semver, deprecation policy, supported platforms). engineering: contracts (public API), mechanism, failure |
| **Configuration / feature flags** | behaviour depends on state nobody can see | product: which flags change user-visible behaviour and who may flip them. engineering: where flags live, defaults, kill-switch procedure |

If something does not fit any row, ask: *who would be asked this, and what shape is
the answer?* That gives the domain and the section shape. The topic is whatever noun
that person uses.

## 8. Maintenance rules

- A change in behaviour changes the section body **and** the blurb if the blurb no
  longer says what the section answers.
- Adding a section means adding an index entry. The linter refuses the file otherwise.
- When a route is wrong in practice, the fix is almost always to the summary or the
  blurb, not to the router. Keep a log of misrouted questions; they are the test set.
- Delete rather than let rot. A section that says "TODO" routes questions to nothing.
