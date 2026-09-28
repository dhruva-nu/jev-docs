from pathlib import Path

from jevdocs import lint, load, parse_text
from jevdocs.corpus import lint_file

POC = Path(__file__).parent.parent / "poc" / "docs"

GOOD = """# Inventory

This file contains the rules that govern inventory.
Ask here for why stock levels are what they are.

Related: engineering/inventory.md
Owner: merch

## Index

1. Rules overview — every rule in one list
2. [Book A minimum stock](#book-a-minimum-stock) — why Book A has 20 copies
3. Book B anonymity - why Book B buyers stay anonymous

## Rules overview
All rules.

## Book A minimum stock
Twenty copies.

## Book B anonymity
Anonymous.
"""


def test_parse_file_structure():
    doc = parse_text(GOOD, domain="product")
    assert doc.title == "Inventory"
    assert len(doc.summary) == 2
    assert doc.metadata == {"related": "engineering/inventory.md", "owner": "merch"}
    assert doc.related == ["engineering/inventory.md"]
    assert [s.anchor for s in doc.sections] == ["rules-overview", "book-a-minimum-stock", "book-b-anonymity"]
    assert doc.sections[1].blurb == "why Book A has 20 copies"
    assert doc.sections[2].blurb == "why Book B buyers stay anonymous"
    assert doc.section("Book A minimum stock").body == "Twenty copies."
    assert lint_file(doc) == []


def test_lint_catches_every_rule():
    bad = """# X

Only one summary line.

## Index

1. Alpha
3. Beta — second
2. Gamma — third

## Alpha
### nested
text

## Beta
TODO write this

## Orphan
nobody indexes me
"""
    messages = " | ".join(p.message for p in lint_file(parse_text(bad)))
    assert "summary has 1 lines" in messages
    assert "has no blurb" in messages
    assert "numbered 3, expected 2" in messages
    assert "no matching `## Gamma`" in messages
    assert "H3 headings" in messages
    assert "TODO" in messages
    assert "`## Orphan` is not in the index" in messages


def test_index_size_limits():
    many = "# X\n\na\nb\n\n## Index\n\n" + "".join("%d. S%d — s\n" % (i, i) for i in range(1, 14))
    many += "".join("\n## S%d\nbody\n" % i for i in range(1, 14))
    assert any("index has 13 entries" in p.message for p in lint_file(parse_text(many)))


def test_poc_docs_are_clean_and_twins_resolve():
    corpus = load(POC)
    assert lint(corpus) == []
    assert set(corpus.domains) == {"product", "engineering"}
    assert corpus.get("product/inventory.md").related[0] == "engineering/inventory.md"
    assert "HOW" in corpus.domains["engineering"].description


def test_missing_related_is_reported(tmp_path):
    (tmp_path / "product").mkdir()
    (tmp_path / "product" / "a.md").write_text(GOOD.replace("engineering/inventory.md", "engineering/nope.md"))
    problems = lint(load(tmp_path))
    assert any("missing file 'engineering/nope.md'" in p.message for p in problems)
