# jev-docs

Route a reader's question to the one documentation section that answers it, using
the [Jev System One API](../jev-sdk) instead of embeddings or generated text.

```
"why do we have 20 copies of Book A in inventory?"
   -> domain: product    (p=0.91)
   -> file:   product/inventory.md   (p=0.88)
   -> section: #book-a-minimum-stock (p=0.83)
```

Three hops, each a calibrated `Choice` over things the docs author wrote for exactly
this purpose: the domain descriptions, the file summaries, the index blurbs. The router
never reads section bodies, so the docs format is what makes routing work.
Read **[DOCS_FORMAT.md](DOCS_FORMAT.md)** first. **[PLAN.md](PLAN.md)** has the
implementation plan and what is left.

## Layout

```
DOCS_FORMAT.md        how to write docs so any software fits (the contract)
PLAN.md               implementation plan and status
src/jevdocs/          the engine
  corpus.py           parse a docs tree, lint it
  questions.py        build the Jev questions for each hop
  router.py           Router: question -> Route (domain, file, section, twin, confidences)
  mock.py             offline stand-in for the Jev API (lexical, uncalibrated)
  cli.py              jevdocs route | lint | tree | eval
poc/                  detached proof of concept: bookstore docs, eval set, standalone poc.py
tests/                offline tests
```

## Run the POC web page

```bash
uv sync
uv run poc/server.py                      # open http://127.0.0.1:8765
JEV_API_KEY=... uv run poc/server.py      # same page against the real Jev API
```

Ask a question and the page shows the answer section, then every step: what Jev was asked,
every option it chose between with the text it read, the probability of each, the
confidence, and the path probability. The file step keeps the top two files; the section
step asks inside both in one request; a final relevance step reads each candidate
section's text and asks Jev whether it is relevant. The answer is the most probable
candidate that passes, or, when none passes, the most probable one marked unverified. The dropdown opens any doc, with the routed section
highlighted. `?q=...` in the URL asks straight away, so a route can be shared as a link.
The POC uses only the jev SDK; it shares the docs with the engine but none of its code.

Each answer also shows the time it took and its price in rupees. Time is shown three ways: in
the browser, on the server, and inside each Jev call. Price uses TypeSafe's listed rate of
$0.042 per million input tokens, with output tokens free, converted at ₹95.9 per dollar
(the 26 September 2026 rate). Override either rate without editing code:

```bash
JEV_USD_PER_MTOK=0.042 JEV_INR_PER_USD=96.2 uv run poc/server.py
```

Under the mock, token counts are estimates and times are near zero.

## Run the engine

```bash
uv run jevdocs lint --docs poc/docs
uv run jevdocs tree --docs poc/docs
uv run jevdocs route "why do we have 20 copies of Book A?" --docs poc/docs --show
uv run jevdocs eval poc/questions.jsonl --docs poc/docs
uv run poc/poc.py --mock                  # the standalone POC (jev SDK only, no engine code)

JEV_API_KEY=... uv run jevdocs eval poc/questions.jsonl --docs poc/docs --live
```

Without `JEV_API_KEY` the commands use the mock, which answers by keyword overlap
through the real SDK client and `httpx.MockTransport`. It proves the plumbing, not the
routing quality.

## Use the engine

```python
from jev import Jev
from jevdocs import load, lint, Router

corpus = load("docs")
assert not lint(corpus)
router = Router(corpus, Jev())
route = router.route("how is the Book A restock enforced?")
route.ref          # "engineering/inventory.md#restock-job"
route.text         # the section body
route.status       # "ok" | "ambiguous" | "not_documented"
route.also         # the product twin's route when the question spans why and how
route.explain()
```
