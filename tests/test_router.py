"""Router logic against a scripted API: each test decides what Jev 'answers'."""
import json
from pathlib import Path

import httpx
import pytest
from jev import Jev

from jevdocs import AMBIGUOUS, NOT_DOCUMENTED, OK, UNVERIFIED, Router, load, mock_client

POC = Path(__file__).parent.parent / "poc" / "docs"


@pytest.fixture(scope="module")
def corpus():
    return load(POC)


def scripted(picks, nouls=None, sent=None):
    """picks: {question kind: label or {label: prob}}, where kind drops a `_N` suffix
    (section_0 and section_1 both use picks["section"]); labels a file lacks are ignored.
    nouls: {name: probability or callable(state) -> probability}."""
    nouls = {"answerable": 0.9, "spans_domains": 0.1, "whole_file": 0.1, "relevant": 0.9, **(nouls or {})}

    def kind(name):
        base, _, suffix = name.rpartition("_")
        return base if suffix.isdigit() else name

    def handler(request):
        body = json.loads(request.content)
        if sent is not None:
            sent.append(body)
        answers = {}
        for name, q in body["questions"].items():
            if q["type"] == "noul":
                value = nouls[kind(name)]
                answers[name] = {"type": "noul", "noul": value(body["state"]) if callable(value) else value}
                continue
            labels = list(q["criteria"])
            want = picks[kind(name)]
            want = {want: 0.9} if isinstance(want, str) else want
            want = {l: p for l, p in want.items() if l in labels}
            rest = (1 - sum(want.values())) / max(len(labels) - len(want), 1)
            probs = {l: want.get(l, rest) for l in labels}
            top = sorted(probs.values(), reverse=True)
            answers[name] = {"type": "choice", "choice": max(probs, key=probs.get),
                             "confidence": top[0] - top[1], "probabilities": probs}
        return httpx.Response(200, json={"model": "scripted", "answers": answers, "usage": {"input_tokens": 10}})

    return Jev("k", http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def section_title(state):
    return state["documentation_section"]["title"]


def test_three_hops_to_a_section(corpus):
    sent = []
    jev = scripted({"domain": "product", "topic": "inventory", "section": "book-a-minimum-stock"}, sent=sent)
    route = Router(corpus, jev).route("why do we have 20 copies of Book A?")
    assert route.status == OK
    assert route.ref == "product/inventory.md#book-a-minimum-stock"
    assert "partner contract" in route.text
    assert route.requests == 5 and route.input_tokens == 50  # domain, file, sections, 2 checks
    assert route.relevance == 0.9 and route.verified
    # hop 1 asks all three router questions together; hop 2 offers only product files
    assert set(sent[0]["questions"]) == {"domain", "answerable", "spans_domains"}
    assert set(sent[1]["questions"]["topic"]["criteria"]) == set(corpus.domains["product"].files)
    assert "Book A" in sent[1]["questions"]["topic"]["criteria"]["inventory"]
    # hop 3 asks sections of the top two files in ONE request
    assert set(sent[2]["questions"]) == {"section_0", "whole_file_0", "section_1", "whole_file_1"}
    # the checks read the section text
    checks = [b for b in sent[3:] if "relevant" in b["questions"]]
    assert len(checks) == 2
    assert any("partner contract" in b["state"]["documentation_section"]["text"] for b in checks)


def test_not_documented_stops_after_one_request(corpus):
    jev = scripted({"domain": "product"}, nouls={"answerable": 0.05})
    route = Router(corpus, jev).route("what's the weather?")
    assert route.status == NOT_DOCUMENTED
    assert route.ref is None and route.requests == 1


def test_spanning_question_follows_the_twin(corpus):
    picks = {"domain": "product", "topic": "inventory", "section": {"book-a-minimum-stock": 0.5, "book-a-restock-job": 0.45}}
    route = Router(corpus, scripted(picks, nouls={"spans_domains": 0.9})).route("why 20 and how is it enforced?")
    assert route.ref == "product/inventory.md#book-a-minimum-stock"
    assert route.also is not None
    assert route.also.ref == "engineering/inventory.md#book-a-restock-job"
    assert route.also.relevance == 0.9
    assert route.requests == 5 + 2  # plus the twin's section request and its check


def test_twin_found_by_related_even_with_a_different_name(corpus):
    picks = {"domain": "product", "topic": "reporting", "section": "why-numbers-lag-a-day"}
    route = Router(corpus, scripted({**picks, "section": {"why-numbers-lag-a-day": 0.6, "schedule-and-steps": 0.3}},
                                    nouls={"spans_domains": 0.9})).route("why a day late and how does the job run?")
    assert route.also.file.ref == "engineering/reconciliation.md"


def test_unsure_domain_searches_every_domain(corpus):
    picks = {"domain": {"product": 0.52, "engineering": 0.48}, "topic": "inventory", "section": "tables"}
    route = Router(corpus, scripted(picks)).route("stock table?")
    assert route.searched_domains == ["product", "engineering"]
    assert route.requests == 6  # domain, two file hops, sections, two checks


def test_low_section_probability_is_ambiguous(corpus):
    picks = {"domain": "engineering", "topic": "inventory", "section": {"tables": 0.3, "api-contracts": 0.29}}
    route = Router(corpus, scripted(picks)).route("stock?")
    assert route.status == AMBIGUOUS
    assert route.alternatives()[0].startswith("engineering/")


def test_whole_file_answer(corpus):
    picks = {"domain": "product", "topic": "pricing", "section": "discount-rules"}
    route = Router(corpus, scripted(picks, nouls={"whole_file": 0.9})).route("tell me everything about pricing")
    assert "## Rounding" in route.text and "## Price matching" in route.text


def test_mock_backend_routes_the_headline_question(corpus):
    route = Router(corpus, mock_client(corpus)).route("Why do we have 20 copies of Book A in inventory?")
    assert route.ref == "product/inventory.md#book-a-minimum-stock"
    assert route.to_dict()["domain"]["chosen"] == "product"


def test_top_two_files_candidate_with_higher_score_wins(corpus):
    # inventory is the likelier file, but its best section is weak; permissions has a sure section
    picks = {"domain": "product",
             "topic": {"inventory": 0.55, "permissions": 0.40},
             "section": {"book-b-buyer-anonymity": 0.4, "who-may-see-customer-data": 0.95}}
    route = Router(corpus, scripted(picks)).route("who can see Book B buyers?")
    assert [c.file.name for c in route.checked] == ["permissions", "inventory"]  # 0.38 beats 0.22
    assert route.ref == "product/permissions.md#who-may-see-customer-data"


def test_relevance_check_overrides_a_higher_score(corpus):
    picks = {"domain": "product", "topic": {"inventory": 0.6, "reporting": 0.35},
             "section": {"book-a-minimum-stock": 0.9, "which-number-wins": 0.9}}
    relevant = lambda state: 0.1 if section_title(state) == "Book A minimum stock" else 0.95
    route = Router(corpus, scripted(picks, nouls={"relevant": relevant})).route("22 vs 18, which count is right?")
    assert route.checked[0].file.name == "inventory"  # higher score...
    assert route.ref == "product/reporting.md#which-number-wins"  # ...but failed the check
    assert route.status == OK and route.relevance == 0.95
    assert any("failed the relevance check" in n for n in route.notes)


def test_no_relevant_candidate_is_unverified(corpus):
    picks = {"domain": "product", "topic": "inventory", "section": "rules-overview"}
    route = Router(corpus, scripted(picks, nouls={"relevant": 0.2})).route("something odd")
    assert route.status == UNVERIFIED and not route.verified
    assert route.ref == route.checked[0].ref  # still the most probable route


def test_verify_and_top_files_can_be_turned_off(corpus):
    picks = {"domain": "product", "topic": "inventory", "section": "book-a-minimum-stock"}
    route = Router(corpus, scripted(picks), top_files=1, verify=False).route("book a?")
    assert route.requests == 3 and route.relevance is None and len(route.checked) == 1
