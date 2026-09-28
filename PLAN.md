# Implementation plan

## Done (v0.1)

| piece | where | what it does |
| --- | --- | --- |
| Format spec | `DOCS_FORMAT.md` | the contract: tree, file anatomy, topic and section boundaries, how hard software fits |
| Parser + linter | `src/jevdocs/corpus.py` | loads `docs/<domain>/<topic>.md`, enforces the format |
| Question builders | `src/jevdocs/questions.py` | one Jev question set per hop, built from what the docs author wrote |
| Router | `src/jevdocs/router.py` | question -> `Route` with probabilities, status, candidates, twin |
| Offline mock | `src/jevdocs/mock.py` | a real `jev.Jev` over `httpx.MockTransport`, answering by keyword overlap |
| CLI | `src/jevdocs/cli.py` | `route`, `lint`, `tree`, `eval` |
| POC | `poc/` | 14 bookstore docs, 28 eval questions, a standalone `poc.py` using only the jev SDK |
| Tests | `tests/` | parser, linter, every router branch against a scripted API |

## How a route is made

```
hop 1  one request   domain Choice + answerable Noul + spans_domains Noul
        answerable < 0.30            -> status not_documented, stop
        domain confidence < 0.25     -> search every domain in hop 2, keep the best
hop 2  one request per searched domain
        topic Choice, one option per file, described by its summary + section titles
        p < 0.35                     -> status ambiguous (still routed, with candidates)
hop 3  one request   for each of the top 2 files: section Choice + needs_whole_file Noul
        score = P(file) x P(section | file)
check  one request per candidate, in parallel: "relevant" Noul over {question, section text}
        pick the highest score with P(relevant) >= 0.7
        none passes                  -> status unverified (still the highest score)
        p(file or section) < 0.35    -> status ambiguous
        needs_whole_file >= 0.6      -> route.text is the whole file
twin   spans_domains >= 0.6          -> follow Related: (or the same-named file in the
                                        other domain) and run hop 3 there -> route.also
```

Typical cost is 5 requests per question (4 round trips, the checks run in parallel), 7 with
a twin. `Router(top_files=1, verify=False)` gives the old 3-request behaviour.
Every threshold is a `Router(...)` argument.

## Next

1. **Run the eval live.** `JEV_API_KEY=... uv run jevdocs eval poc/questions.jsonl --live`.
   The mock only proves plumbing; calibrate the thresholds on real probabilities.
2. **Parallel hops.** Hop 2 across domains and the twin's hop 3 are independent; use
   `AsyncJev` to cut latency when they fan out.
3. **Cache question definitions per corpus version.** They are rebuilt per `Router`; hash the
   corpus and reuse across processes.
4. **Misroute log.** Record every `ambiguous` route and every user correction as a new eval line.
   Per DOCS_FORMAT.md §8, the fix is usually a summary or blurb, not the router.
5. **Scale past ~30 files per domain.** A single Choice over many summaries gets diluted. Add
   an optional `group:` metadata line and a hop between domain and file, or shortlist with a
   cheap lexical pass before the Choice.
6. **Serve it.** Wrap `Router.route` in an HTTP endpoint or an MCP tool so agents can call it.
7. **Authoring aids.** `jevdocs new <domain> <topic>` to scaffold a file, and a sibling-overlap
   check that asks Jev whether two summaries could answer the same question.
