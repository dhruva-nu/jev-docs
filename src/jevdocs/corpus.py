"""Load a docs tree written in the jev-docs format (see DOCS_FORMAT.md) into a Corpus.

    docs/
      product/inventory.md
      engineering/inventory.md

Each file: `# Title`, a 2-5 line summary, optional `Related:` / `Owner:` lines, an
`## Index` list of `N. Title — blurb`, then one `## Title` section per index entry.

    corpus = load("poc/docs")
    corpus.domains["product"].files["inventory"].sections[1].blurb
    for problem in lint(corpus): print(problem)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional

DEFAULT_DOMAIN_DESCRIPTIONS = {
    "product": (
        "WHY things are the way they are: rules, policies, promises to users, business reasons, "
        "decisions and their history, what the user sees or is allowed to do. "
        "Question words: why, what is the rule, what do we promise, who decided, is it allowed."
    ),
    "engineering": (
        "HOW it is built and enforced: APIs, endpoints, tables, schemas, services, jobs, cron, "
        "code paths, configs, runbooks, deploys, the mechanism behind a rule. "
        "Question words: how, where in the code, which table, which endpoint, which job, how do I run it."
    ),
}

METADATA_KEYS = ("related", "owner", "see also", "status")
INDEX_TITLE = "index"
BLURB_SEPARATORS = (" — ", " – ", " - ", ": ")


@dataclass
class Section:
    number: int
    title: str
    blurb: str
    body: str = ""
    line: int = 0

    @property
    def anchor(self) -> str:
        return slug(self.title)


@dataclass
class DocFile:
    domain: str
    name: str  # file stem, e.g. "inventory"
    path: Path
    title: str
    summary: List[str]
    metadata: Dict[str, str]
    sections: List[Section]
    orphans: List[tuple] = field(default_factory=list)  # (heading, line) of H2s missing from the index

    @property
    def related(self) -> List[str]:
        raw = self.metadata.get("related", "")
        return [r.strip() for r in re.split(r"[,;]", raw) if r.strip()]

    def summary_text(self) -> str:
        return " ".join(self.summary)

    def section(self, anchor_or_title: str) -> Optional[Section]:
        key = slug(anchor_or_title)
        return next((s for s in self.sections if s.anchor == key), None)

    @property
    def ref(self) -> str:
        return "%s/%s.md" % (self.domain, self.name)


@dataclass
class Domain:
    name: str
    description: str
    files: Dict[str, DocFile] = field(default_factory=dict)


@dataclass
class Corpus:
    root: Path
    domains: Dict[str, Domain]

    def files(self) -> Iterator[DocFile]:
        for d in self.domains.values():
            yield from d.files.values()

    def get(self, ref: str) -> Optional[DocFile]:
        """Look a file up by `domain/name.md` or `domain/name`."""
        ref = ref.strip().removesuffix(".md")
        domain, _, name = ref.partition("/")
        return self.domains.get(domain, Domain("", "")).files.get(name)

    def vocabulary(self) -> set:
        words: set = set()
        for f in self.files():
            words |= tokens(f.title + " " + f.summary_text())
            for s in f.sections:
                words |= tokens(s.title + " " + s.blurb + " " + s.body)
        return words


# ----------------------------------------------------------------------------- loading
def load(root: str | Path, domains: Optional[List[str]] = None) -> Corpus:
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError("docs root %s is not a directory" % root)
    found: Dict[str, Domain] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if domains and d.name not in domains:
            continue
        found[d.name] = Domain(d.name, _domain_description(d), {})
        for md in sorted(d.glob("*.md")):
            if md.name.lower() == "readme.md":
                continue
            found[d.name].files[md.stem] = parse_file(md, d.name)
    if not found:
        raise ValueError("no domain directories under %s" % root)
    return Corpus(root, found)


def _domain_description(domain_dir: Path) -> str:
    readme = domain_dir / "README.md"
    if readme.exists():
        lines = [l.strip() for l in readme.read_text().splitlines()]
        lines = [l for l in lines if l and not l.startswith("#")]
        if lines:
            return " ".join(lines[:5])
    return DEFAULT_DOMAIN_DESCRIPTIONS.get(domain_dir.name, "documentation under %s/" % domain_dir.name)


def parse_file(path: Path, domain: str) -> DocFile:
    return parse_text(path.read_text(), path=path, domain=domain)


def parse_text(text: str, path: Path = Path("<memory>.md"), domain: str = "") -> DocFile:
    lines = text.splitlines()
    title = ""
    summary: List[str] = []
    metadata: Dict[str, str] = {}
    index: List[Section] = []
    bodies: Dict[str, tuple] = {}  # anchor -> (title, body, line)

    i = 0
    n = len(lines)
    # H1
    while i < n and not lines[i].strip():
        i += 1
    if i < n and lines[i].startswith("# "):
        title = lines[i][2:].strip()
        i += 1
    # summary + metadata until the first H2
    while i < n and not lines[i].startswith("## "):
        line = lines[i].strip()
        if line:
            key, _, value = line.partition(":")
            if key.strip().lower() in METADATA_KEYS and value.strip():
                metadata[key.strip().lower()] = value.strip()
            else:
                summary.append(line)
        i += 1
    # H2 blocks
    while i < n:
        heading = lines[i][3:].strip()
        start = i + 1
        i += 1
        while i < n and not lines[i].startswith("## "):
            i += 1
        block = lines[start:i]
        if heading.lower() == INDEX_TITLE:
            index = _parse_index(block, start)
        else:
            bodies[slug(heading)] = (heading, "\n".join(block).strip(), start)

    # attach bodies to index entries; keep unindexed sections for the linter
    sections: List[Section] = []
    for entry in index:
        body = bodies.pop(entry.anchor, None)
        if body:
            entry.body, entry.line = body[1], body[2]
        sections.append(entry)
    orphans = [(heading, line) for heading, _, line in bodies.values()]
    return DocFile(domain, path.stem, path, title or path.stem, summary, metadata, sections, orphans)


_INDEX_ENTRY = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
_LINK = re.compile(r"^\[(.*?)\]\(#.*?\)\s*(.*)$")


def _parse_index(block: List[str], start_line: int) -> List[Section]:
    entries: List[Section] = []
    for offset, raw in enumerate(block):
        m = _INDEX_ENTRY.match(raw)
        if not m:
            continue
        number, rest = int(m.group(1)), m.group(2).strip()
        link = _LINK.match(rest)
        if link:
            title, rest = link.group(1).strip(), link.group(2).strip()
            blurb = rest.lstrip("—–-: ").strip()
        else:
            title, blurb = rest, ""
            for sep in BLURB_SEPARATORS:
                if sep in rest:
                    title, blurb = (p.strip() for p in rest.split(sep, 1))
                    break
        entries.append(Section(number, title, blurb, line=start_line + offset + 1))
    return entries


# ----------------------------------------------------------------------------- lint
SUMMARY_LINES = (2, 5)
INDEX_ENTRIES = (3, 12)


@dataclass(frozen=True)
class Problem:
    file: str
    message: str
    line: int = 0

    def __str__(self):
        loc = "%s:%d" % (self.file, self.line) if self.line else self.file
        return "%s: %s" % (loc, self.message)


def lint(corpus: Corpus) -> List[Problem]:
    problems: List[Problem] = []
    for doc in corpus.files():
        problems.extend(lint_file(doc))
        for ref in doc.related:
            if corpus.get(ref) is None:
                problems.append(Problem(doc.ref, "Related: points at missing file %r" % ref))
    for domain in corpus.domains.values():
        if not domain.files:
            problems.append(Problem(domain.name + "/", "domain has no topic files"))
    return problems


def lint_file(doc: DocFile) -> List[Problem]:
    p: List[Problem] = []
    ref = doc.ref if doc.domain else doc.path.name
    if not doc.title:
        p.append(Problem(ref, "missing `# Title` on the first line", 1))
    lo, hi = SUMMARY_LINES
    if not lo <= len(doc.summary) <= hi:
        p.append(Problem(ref, "summary has %d lines; want %d-%d" % (len(doc.summary), lo, hi), 2))
    lo, hi = INDEX_ENTRIES
    if not doc.sections:
        p.append(Problem(ref, "missing `## Index`"))
    elif not lo <= len(doc.sections) <= hi:
        p.append(Problem(ref, "index has %d entries; want %d-%d (merge or split the topic)" % (len(doc.sections), lo, hi)))
    for expected, s in enumerate(doc.sections, start=1):
        if s.number != expected:
            p.append(Problem(ref, "index entry %r is numbered %d, expected %d" % (s.title, s.number, expected), s.line))
        if not s.blurb:
            p.append(Problem(ref, "index entry %r has no blurb after ` — `" % s.title, s.line))
        if not s.body:
            p.append(Problem(ref, "index entry %r has no matching `## %s` section" % (s.title, s.title), s.line))
        elif "### " in s.body:
            p.append(Problem(ref, "section %r contains H3 headings; promote them to sections or split the file" % s.title, s.line))
        elif "todo" in s.body.lower()[:200]:
            p.append(Problem(ref, "section %r starts with a TODO; write it or delete it" % s.title, s.line))
    for heading, line in doc.orphans:
        p.append(Problem(ref, "section `## %s` is not in the index" % heading, line))
    # sections in index order should appear in file order
    lines = [s.line for s in doc.sections if s.body]
    if lines != sorted(lines):
        p.append(Problem(ref, "sections are not in index order"))
    return p


# ----------------------------------------------------------------------------- helpers
def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


_WORD = re.compile(r"[a-z0-9][a-z0-9'+-]*")


def tokens(text: str) -> set:
    return set(_WORD.findall(text.lower()))
