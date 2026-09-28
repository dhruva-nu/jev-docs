"""A self-contained proof of concept of docs routing with Jev.

It imports nothing from the jevdocs engine: only the jev SDK and the standard library,
so it can be read top to bottom in one sitting and copied anywhere.

    uv run poc/server.py                                           # the web page, http://127.0.0.1:8765
    uv run poc/poc.py "why do we have 20 copies of Book A?"      # real API if JEV_API_KEY is set
    uv run poc/poc.py --mock "how do I roll back a deploy?"        # offline keyword stand-in

Four steps:
  1. product or engineering?          one Choice over the two domain descriptions
  2. which file in that domain?       one Choice over each file's summary; keep the top two
  3. which section of each?           one request, a Choice over each top file's `## Index`
  4. is that section relevant?        a yes/no per candidate, in parallel, reading the text
The answer is the most probable candidate that passes step 4, with every step's full
probability distribution, the time it took and its price.
"""
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import httpx
from concurrent.futures import ThreadPoolExecutor

from jev import Jev, choice, noul

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


load_dotenv(Path(__file__).parent.parent / ".env")  # the repo root .env holds JEV_API_KEY

DOCS = Path(__file__).parent / "docs"
LOW_CONFIDENCE = 0.15

# Price. TypeSafe lists Jev at $0.042 per million input tokens; output tokens are free.
# https://typesafe.ai/blog/introducing-system-one-models-and-jev
# The rupee rate is the mid-market rate on 2026-09-26; override both without editing code.
USD_PER_MILLION_INPUT = float(os.environ.get("JEV_USD_PER_MTOK", "0.042"))
INR_PER_USD = float(os.environ.get("JEV_INR_PER_USD", "95.9"))


def pricing():
    return {"usd_per_million_input": USD_PER_MILLION_INPUT, "inr_per_usd": INR_PER_USD,
            "inr_per_million_input": USD_PER_MILLION_INPUT * INR_PER_USD, "output": "free"}


def cost_inr(input_tokens):
    return input_tokens / 1e6 * USD_PER_MILLION_INPUT * INR_PER_USD

DEMO = [
    "Why do we have 20 copies of Book A in inventory?",
    "Which cron job keeps Book A restocked?",
    "Why does every order get 7% off?",
    "How do I roll back a bad storefront deploy?",
    "Why do downloaded books expire after 30 days offline?",
]


# --------------------------------------------------------------------------- read the docs
def read_docs(root=DOCS):
    """{domain: {"about": str, "files": {name: {"title", "summary", "related", "text", "sections"}}}}"""
    tree = {}
    for domain_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        readme = domain_dir / "README.md"
        about = " ".join(l for l in readme.read_text().splitlines() if l and not l.startswith("#")) if readme.exists() else domain_dir.name
        files = {}
        for md in sorted(domain_dir.glob("*.md")):
            if md.name != "README.md":
                files[md.stem] = read_file(md.read_text())
        tree[domain_dir.name] = {"about": about, "files": files}
    return tree


def read_file(text):
    head, _, rest = text.partition("\n## Index\n")
    head_lines = head.splitlines()
    title = head_lines[0].lstrip("# ").strip() if head_lines else ""
    summary = " ".join(l.strip() for l in head_lines[1:] if l.strip() and not re.match(r"^(Related|Owner):", l))
    related = next((l.split(":", 1)[1].strip() for l in head_lines if l.startswith("Related:")), "")
    index_block, _, bodies = rest.partition("\n## ")
    bodies = "## " + bodies
    body_of = {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", bodies, re.S | re.M)}
    sections = []
    for line in index_block.splitlines():
        m = re.match(r"^\d+\.\s+(.+?)\s+[—-]\s+(.+)$", line.strip())
        if m:
            sections.append({"anchor": anchor(m.group(1)), "title": m.group(1), "blurb": m.group(2),
                             "body": body_of.get(m.group(1), "")})
    return {"title": title, "summary": summary, "related": related, "text": text, "sections": sections}


def anchor(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


# --------------------------------------------------------------------------- route
TOP_FILES = 2              # how many files the section step looks inside
RELEVANT_AT = 0.7          # P(relevant) needed to pass: correct live routes score 0.86+, wrong ones 0.51-0.63

SECTION_INSTRUCTIONS = "The state is a reader's question, already known to be about %r (%s). Which section of that file answers it?"
RELEVANCE = {
    "instructions": "The state holds a reader's question and one section of our documentation. "
                    "Is this section relevant to the question: does it contain the information the reader is asking for?",
    "true_means": "the section answers the question, fully or in part",
    "false_means": "the section is about something else, or only shares some of the same words",
}


def describe(answer, options):
    """A Choice answer as the page shows it: every option, best first, with what Jev read."""
    ranked = sorted(answer.probabilities.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "chosen": answer.choice,
        "probability": answer.probability,
        "confidence": answer.confidence,
        "low_confidence": answer.confidence < LOW_CONFIDENCE,
        "options": [{"label": label, "description": options[label], "probability": p} for label, p in ranked],
    }


def cost(result, ms=None):
    return {
        "model": result.model,
        "input_tokens": result.usage.input_tokens,
        "cost_inr": cost_inr(result.usage.input_tokens),
        "ms": round((result.elapsed or 0) * 1000 if ms is None else ms, 1),
        "request_id": result.request_id,
    }


def ask_step(jev, question, step, instructions, options):
    """One Jev Choice. Returns everything that was sent and everything that came back."""
    Q = choice(step, instructions, options)
    result = jev.ask(question, Q)
    return {"kind": "choice", "step": step, "instructions": instructions,
            **describe(result[Q], options), **cost(result)}


def sections_step(jev, question, files):
    """ONE request holding a section Choice for each candidate file: [(ref, doc, P(file))]."""
    asked = []
    for i, (ref, doc, p_file) in enumerate(files):
        options = {s["anchor"]: "%s: %s" % (s["title"], s["blurb"]) for s in doc["sections"]}
        asked.append((ref, doc, p_file, options, choice("section_%d" % i, SECTION_INSTRUCTIONS % (doc["title"], doc["summary"]), options)))
    result = jev.ask(question, *[q for *_, q in asked])
    candidates = []
    for ref, doc, p_file, options, q in asked:
        d = describe(result[q], options)
        section = next(s for s in doc["sections"] if s["anchor"] == d["chosen"])
        candidates.append({"file": ref, "file_probability": p_file, "score": p_file * d["probability"],
                           "section": section, "instructions": SECTION_INSTRUCTIONS % (doc["title"], doc["summary"]), **d})
    return {"kind": "sections", "step": "section", "candidates": candidates, **cost(result)}


def relevance_step(jev, question, candidates):
    """One yes/no request per candidate, in parallel: the only step that reads a section's text."""
    Relevant = noul("relevant", RELEVANCE["instructions"], RELEVANCE["true_means"], RELEVANCE["false_means"])

    def check(c):
        state = {"question": question,
                 "documentation_section": {"file": c["file"], "title": c["section"]["title"], "text": c["section"]["body"]}}
        return jev.ask(state, Relevant)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
        results = list(pool.map(check, candidates))
    wall_ms = (time.perf_counter() - started) * 1000
    checks = []
    for c, r in zip(candidates, results):
        p = r[Relevant].probability
        checks.append({"ref": "%s#%s" % (c["file"], c["section"]["anchor"]), "title": c["section"]["title"],
                       "score": c["score"], "relevance": p, "relevant": p >= RELEVANT_AT, **cost(r)})
    tokens = sum(c["input_tokens"] for c in checks)
    return {"kind": "relevance", "step": "relevance", **RELEVANCE, "threshold": RELEVANT_AT, "checks": checks,
            "model": results[0].model, "input_tokens": tokens, "cost_inr": cost_inr(tokens), "ms": round(wall_ms, 1),
            "requests": len(checks)}


def route(jev, tree, question):
    started = time.perf_counter()

    # 1. product or engineering
    domain_step = ask_step(
        jev, question, "domain",
        "Which kind of documentation answers this reader's question? Judge by what the reader wants to know.",
        {name: d["about"] for name, d in tree.items()})
    domain_name = domain_step["chosen"]
    domain = tree[domain_name]

    # 2. which file: keep the top two, not just the winner
    file_step = ask_step(
        jev, question, "file",
        "Which %s documentation file covers this question? Each option is the file's summary." % domain_name,
        {name: f["summary"] for name, f in domain["files"].items()})
    top = file_step["options"][:TOP_FILES]
    file_step["checked"] = [o["label"] for o in top]

    # 3. which section, inside each of the top files, in one request
    files = [("%s/%s.md" % (domain_name, o["label"]), domain["files"][o["label"]], o["probability"]) for o in top]
    section_step = sections_step(jev, question, files)
    candidates = sorted(section_step["candidates"], key=lambda c: c["score"], reverse=True)

    # 4. is the section relevant? read each candidate's text
    relevance = relevance_step(jev, question, candidates)
    by_ref = {c["ref"]: c for c in relevance["checks"]}
    for c in candidates:
        c["relevance"] = by_ref["%s#%s" % (c["file"], c["section"]["anchor"])]["relevance"]

    # pick: the most probable candidate that passes the check, else the most probable, unverified
    passing = [c for c in candidates if c["relevance"] >= RELEVANT_AT]
    chosen = passing[0] if passing else candidates[0]
    ref = "%s#%s" % (chosen["file"], chosen["section"]["anchor"])
    if not passing:
        why = "No candidate passed the relevance check, so this is the most probable route, unverified."
    elif chosen is candidates[0]:
        why = "The most probable route, and its section passed the relevance check."
    else:
        why = ("%s#%s was more probable but failed the relevance check (%.0f%%), so the next candidate was chosen."
               % (candidates[0]["file"], candidates[0]["section"]["anchor"], candidates[0]["relevance"] * 100))
    relevance["chosen"] = ref
    relevance["selection"] = why

    steps = [domain_step, file_step, section_step, relevance]
    return {
        "question": question,
        "route": ref,
        "doc": chosen["file"][:-3],
        "section": chosen["section"]["anchor"],
        "section_title": chosen["section"]["title"],
        "text": chosen["section"]["body"],
        "verified": bool(passing),
        "relevance": chosen["relevance"],
        "selection": why,
        # before reading the text: P(domain) x P(file) x P(section | file)
        "path_probability": domain_step["probability"] * chosen["file_probability"] * chosen["probability"],
        "path_parts": [domain_step["probability"], chosen["file_probability"], chosen["probability"]],
        "steps": steps,
        "requests": 3 + relevance["requests"],
        "input_tokens": sum(s["input_tokens"] for s in steps),
        "cost_inr": sum(s["cost_inr"] for s in steps),
        "pricing": pricing(),
        "jev_ms": round(sum(s["ms"] for s in steps), 1),  # checks run in parallel, so their wall time counts once
        "total_ms": round((time.perf_counter() - started) * 1000, 1),
        "estimated_tokens": domain_step["model"] == "keyword-mock",
    }


# --------------------------------------------------------------------------- offline stand-in
STOPWORDS = set("the and for with that this does are was our you your can from into".split())  # keep why/how/which: they carry the domain


def keyword_mock(request):
    """Answers a Choice by word overlap with each option. Not calibrated; proves the plumbing only."""
    body = json.loads(request.content)
    words = lambda s: {w[:6] for w in re.findall(r"[a-z0-9]+", str(s).lower())
                       if (len(w) > 2 or w.isdigit()) and w not in STOPWORDS}
    q = words(body["state"])
    answers = {}
    for name, spec in body["questions"].items():
        if spec["type"] == "noul":  # relevance: share of the question's words found in the section text
            section = words(body["state"].get("documentation_section", "")) if isinstance(body["state"], dict) else set()
            asked = words(body["state"].get("question", "")) if isinstance(body["state"], dict) else q
            share = len(asked & section) / max(len(asked), 1)
            answers[name] = {"type": "noul", "noul": min(0.97, max(0.03, 1.6 * share - 0.1))}
            continue
        scores = {label: len(q & (words(label) | words(desc))) for label, desc in spec["criteria"].items()}
        z = sum(math.exp(v) for v in scores.values())
        probs = {label: math.exp(v) / z for label, v in scores.items()}
        top = sorted(probs.values(), reverse=True)
        answers[name] = {"type": "choice", "choice": max(probs, key=probs.get),
                         "confidence": top[0] - top[1], "probabilities": probs}
    usage = {"input_tokens": len(request.content) // 4}
    return httpx.Response(200, json={"model": "keyword-mock", "answers": answers, "usage": usage},
                          headers={"x-typesafe-request-id": "mock"})


def use_mock(force=False):
    return force or not os.environ.get("JEV_API_KEY")


def client(mock=False):
    if use_mock(mock):
        return Jev("mock", http_client=httpx.Client(transport=httpx.MockTransport(keyword_mock)))
    return Jev()


def main(argv):
    mock = "--mock" in argv
    questions = [a for a in argv if a != "--mock"] or DEMO
    if use_mock(mock) and not mock:
        print("(JEV_API_KEY not set: using the keyword mock)\n")
    tree = read_docs()
    with client(mock) as jev:
        for q in questions:
            r = route(jev, tree, q)
            print(r["question"])
            for st in r["steps"][:2]:
                print("  %-9s %-30s p=%.2f conf=%.2f%s" % (st["step"], st["chosen"], st["probability"], st["confidence"],
                                                         "   LOW CONFIDENCE" if st["low_confidence"] else ""))
            for c in r["steps"][2]["candidates"]:
                print("  section   %-50s score=%.2f (file %.2f x section %.2f)" % (
                    c["file"] + "#" + c["chosen"], c["score"], c["file_probability"], c["probability"]))
            for c in r["steps"][3]["checks"]:
                print("  relevant  %-50s P=%.2f %s" % (c["ref"], c["relevance"], "pass" if c["relevant"] else "fail"))
            print("  -> %s   (%s, relevance %.2f)" % (r["route"], "verified" if r["verified"] else "UNVERIFIED", r["relevance"]))
            print("     " + r["selection"])
            print("     %.0f ms (Jev %.0f ms), %d input tokens, Rs %.5f" % (r["total_ms"], r["jev_ms"], r["input_tokens"], r["cost_inr"]))
            print("     " + r["text"].splitlines()[0][:110] + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
