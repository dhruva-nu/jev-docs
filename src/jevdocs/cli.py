"""Command line: route, lint, tree, eval.

    jevdocs route "why do we keep 20 copies of Book A?" --docs poc/docs [--mock|--live] [--json] [--show]
    jevdocs lint --docs poc/docs
    jevdocs tree --docs poc/docs
    jevdocs eval poc/questions.jsonl --docs poc/docs

Backend: --live needs JEV_API_KEY; --mock forces the offline stand-in; by default the
real API is used when JEV_API_KEY is set and the mock otherwise (with a notice on stderr).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from jev import Jev

from .corpus import Corpus, lint, load
from .mock import mock_client
from .router import Route, Router


def load_dotenv(path):
    """Set KEY=value lines from a .env file, never overriding what the shell already set."""
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return
    for line in lines:
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main(argv: Optional[List[str]] = None) -> int:
    load_dotenv(".env")  # JEV_API_KEY from the working directory, if present
    ap = argparse.ArgumentParser(prog="jevdocs", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--docs", default=_default_docs(), help="docs root (default: ./docs or ./poc/docs)")

    p = sub.add_parser("route", help="route one question")
    common(p)
    p.add_argument("question")
    _backend_flags(p)
    p.add_argument("--json", action="store_true", help="print the route as JSON")
    p.add_argument("--show", action="store_true", help="also print the routed section text")

    p = sub.add_parser("lint", help="check every file against the format")
    common(p)

    p = sub.add_parser("tree", help="print domains, files, summaries and sections")
    common(p)

    p = sub.add_parser("eval", help="route every question in a JSONL file and score against expectations")
    common(p)
    p.add_argument("file")
    _backend_flags(p)
    p.add_argument("--verbose", "-v", action="store_true", help="explain every route, not only the misses")

    args = ap.parse_args(argv)
    corpus = load(args.docs)
    return {"route": cmd_route, "lint": cmd_lint, "tree": cmd_tree, "eval": cmd_eval}[args.command](args, corpus)


def _default_docs() -> str:
    for candidate in ("docs", "poc/docs"):
        if Path(candidate).is_dir():
            return candidate
    return "docs"


def _backend_flags(p):
    g = p.add_mutually_exclusive_group()
    g.add_argument("--mock", action="store_true", help="use the offline lexical mock")
    g.add_argument("--live", action="store_true", help="use the real Jev API (JEV_API_KEY)")
    p.add_argument("--model", default=None, help="Jev model for --live (default jev-latest)")


def _client(args, corpus: Corpus) -> Jev:
    if args.mock or (not args.live and not os.environ.get("JEV_API_KEY")):
        if not args.mock:
            print("jevdocs: JEV_API_KEY not set, using the offline mock (pass --mock to silence)", file=sys.stderr)
        return mock_client(corpus)
    return Jev(model=args.model) if args.model else Jev()


# ----------------------------------------------------------------------------- commands
def cmd_route(args, corpus: Corpus) -> int:
    problems = lint(corpus)
    if problems:
        print("jevdocs: %d lint problem(s) in the docs; run `jevdocs lint`" % len(problems), file=sys.stderr)
    with _client(args, corpus) as jev:
        route = Router(corpus, jev).route(args.question)
    if args.json:
        print(json.dumps(route.to_dict(), indent=2))
    else:
        print(route.explain(show_text=args.show))
    return 0


def cmd_lint(args, corpus: Corpus) -> int:
    problems = lint(corpus)
    for p in problems:
        print(p)
    n = sum(len(d.files) for d in corpus.domains.values())
    print("%d file(s) in %d domain(s): %s" % (n, len(corpus.domains), "clean" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


def cmd_tree(args, corpus: Corpus) -> int:
    for domain in corpus.domains.values():
        print("%s/   %s" % (domain.name, domain.description[:90] + ("…" if len(domain.description) > 90 else "")))
        for doc in domain.files.values():
            print("  %-26s %s" % (doc.name + ".md", doc.summary_text()[:100]))
            for s in doc.sections:
                print("      %d. %-32s %s" % (s.number, s.title, s.blurb[:80]))
    return 0


def cmd_eval(args, corpus: Corpus) -> int:
    cases = [json.loads(l) for l in Path(args.file).read_text().splitlines() if l.strip() and not l.startswith("#")]
    hits = {"domain": 0, "file": 0, "section": 0, "status": 0}
    counted = {"domain": 0, "file": 0, "section": 0, "status": 0}
    total_requests = total_tokens = 0
    relevance_seen = []  # (route was correct, P(relevant)) for every checked route
    with _client(args, corpus) as jev:
        router = Router(corpus, jev)
        for case in cases:
            route = router.route(case["question"])
            total_requests += route.requests
            total_tokens += route.input_tokens
            got = _observed(route)
            ok = True
            marks = []
            for key in ("status", "domain", "file", "section"):
                if key not in case:
                    continue
                counted[key] += 1
                match = _matches(key, case[key], route)
                hits[key] += match
                ok &= match
                marks.append("%s%s" % ("✓" if match else "✗", key))
            rel = "" if route.relevance is None else "  relevant=%.2f" % route.relevance
            print("%s  %-70s -> %s   [%s]%s" % ("PASS" if ok else "MISS", case["question"][:70], got, " ".join(marks), rel))
            if route.relevance is not None:
                relevance_seen.append((ok, route.relevance))
            if args.verbose or not ok:
                print("      expected: %s" % ", ".join("%s=%s" % (k, case[k]) for k in ("status", "domain", "file", "section") if k in case))
                print("      " + route.explain().replace("\n", "\n      "))
    print()
    for key in ("status", "domain", "file", "section"):
        if counted[key]:
            print("%-8s %d/%d" % (key, hits[key], counted[key]))
    if relevance_seen:
        right = [r for ok, r in relevance_seen if ok]
        wrong = [r for ok, r in relevance_seen if not ok]
        avg = lambda xs: sum(xs) / len(xs) if xs else float("nan")
        print("relevant mean P=%.2f on correct routes (%d), P=%.2f on wrong routes (%d)" % (avg(right), len(right), avg(wrong), len(wrong)))
    print("cost     %d requests, %d input tokens, %.1f requests/question" % (total_requests, total_tokens, total_requests / max(len(cases), 1)))
    return 0 if all(hits[k] == counted[k] for k in hits) else 1


def _observed(route: Route) -> str:
    out = route.ref or route.status
    if route.also and route.also.ref:
        out += " + " + route.also.ref
    return out


def _matches(key: str, expected, route: Route) -> bool:
    """`expected` may be a string or a list of acceptable strings. The `also` route counts."""
    accepted = expected if isinstance(expected, list) else [expected]
    routes = [route] + ([route.also] if route.also else [])
    for r in routes:
        if key == "status" and r is route and r.status in accepted:
            return True
        if key == "domain" and r.file and r.file.domain in accepted:
            return True
        if key == "file" and r.file and (r.file.name in accepted or r.file.ref in accepted):
            return True
        if key == "section" and r.section_obj and r.section_obj.anchor in accepted:
            return True
    return False
