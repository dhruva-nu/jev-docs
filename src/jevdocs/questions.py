"""Turn a Corpus into Jev questions. One builder per routing hop.

    DomainQ, Answerable, SpansDomains = domain_questions(corpus)
    TopicQ   = topic_question(corpus.domains["product"])
    SectionQ = section_question(docfile, name="section_0")
    Relevant = relevance_question()             # asked about {question, section text}

Every question is a Choice / Noul built at runtime with the SDK factories, so the
labels are the domain names, file stems and section anchors the caller already has.
"""
from __future__ import annotations

from typing import Dict, Tuple, Type

from jev import Choice, Noul, choice, noul

from .corpus import Corpus, DocFile, Domain

DOMAIN = "domain"
ANSWERABLE = "answerable"
SPANS_DOMAINS = "spans_domains"
TOPIC = "topic"
SECTION = "section"
NEEDS_WHOLE_FILE = "needs_whole_file"
RELEVANT = "relevant"


def domain_questions(corpus: Corpus) -> Tuple[Type[Choice], Type[Noul], Type[Noul]]:
    names = list(corpus.domains)
    domain_q = choice(
        DOMAIN,
        "The state is a question a reader asked about our software. Which kind of documentation "
        "answers it? Judge by what the reader wants to know, not by the nouns they mention.",
        {name: corpus.domains[name].description for name in names},
    )
    answerable = noul(
        ANSWERABLE,
        "Is this something written documentation about our software could answer?",
        true_means="a question about how our product behaves, its rules, its code, its operations, or its history",
        false_means="small talk, a request to perform an action, or a question about the outside world",
    )
    spans = noul(
        SPANS_DOMAINS,
        "Does a complete answer need BOTH the business reason and the technical mechanism?",
        true_means="the reader asks why AND how, or asks for the rule together with its implementation",
        false_means="one of the two is enough: either the reason/rule alone, or the mechanism alone",
    )
    return domain_q, answerable, spans


def topic_question(domain: Domain) -> Type[Choice]:
    if len(domain.files) < 2:
        raise ValueError("domain %r needs at least two files to route between" % domain.name)
    criteria: Dict[str, str] = {}
    for name, doc in domain.files.items():
        # The summary is what the author wrote for exactly this purpose; section titles add
        # the concrete nouns a summary may have skipped.
        criteria[name] = "%s. Sections: %s." % (doc.summary_text().rstrip("."), "; ".join(s.title for s in doc.sections))
    return choice(
        TOPIC,
        "The state is a reader's question. Which of these %s documentation files covers it? "
        "Each option is that file's own summary." % domain.name,
        criteria,
    )


def section_question(doc: DocFile, name: str = SECTION) -> Type[Choice]:
    """`name` lets several files' section questions share one request (section_0, section_1, ...)."""
    if len(doc.sections) < 2:
        raise ValueError("%s needs at least two sections to route between" % doc.ref)
    criteria = {s.anchor: "%s — %s" % (s.title, s.blurb) for s in doc.sections}
    return choice(
        name,
        "The state is a reader's question, already known to be about %r (%s). "
        "Which section of that file answers it?" % (doc.title, doc.summary_text()),
        criteria,
    )


def whole_file_question(doc: DocFile, name: str = NEEDS_WHOLE_FILE) -> Type[Noul]:
    return noul(
        name,
        "Does answering this question need the whole %r file rather than one section?" % doc.title,
        true_means="the reader asks for an overview, a full list, or something that cuts across most sections",
        false_means="one section answers it",
    )


def relevance_question() -> Type[Noul]:
    """Asked with state = {question, section text}: the one hop that reads a section body."""
    return noul(
        RELEVANT,
        "The state holds a reader's question and one section of our documentation. "
        "Is this section relevant to the question: does it contain the information the reader is asking for?",
        true_means="the section answers the question, fully or in part",
        false_means="the section is about something else, or only shares some of the same words",
    )


def relevance_state(question: str, doc: DocFile, title: str, text: str) -> dict:
    return {"question": question, "documentation_section": {"file": doc.ref, "title": title, "text": text}}
