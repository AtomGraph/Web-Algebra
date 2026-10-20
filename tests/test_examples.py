"""The examples in examples/ are checked, and - against a LinkedDataHub - run.

Each example is a folder: `instruction.md` (the request in words), `plan.json`
(the plan), an optional `setup.json` (state the plan starts from), and
`expect/*.rq`, SPARQL ASK queries that hold after the plan has run, and an
optional `result.rq`, a SELECT of the data worth showing in its README.md
(written by scripts/document_examples.py from an actual run).

Always, offline:
- every plan is well-formed (tests/plan_check.py);
- an example writes only beneath its own container, `<base><folder>/`, so it
  can be cleaned up without touching anything else;
- every expectation parses as an ASK query.

Live (marker `ldh`, `pytest -m ldh`), against `LDH_BASE` (default
https://localhost:4443/) with the certificate in CERT_PEM_PATH and
CERT_PASSWORD: the example's container is removed, `setup.json` and
`plan.json` run, every expectation is asked of the instance's SPARQL endpoint,
and the container is removed again (kept if WA_KEEP_EXAMPLES is set). A public
source that does not answer skips the example rather than failing it.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
from rdflib.plugins.sparql.parser import parseQuery

from tests.plan_check import check_static
from web_algebra.main import LinkedDataHubSettings
from web_algebra.operation import Operation

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted(p.parent for p in (ROOT / "examples").glob("*/plan.json"))
WRITTEN_BASE = "https://localhost:4443/"


def _plans(example: Path):
    return [example / name for name in ("setup.json", "plan.json") if (example / name).exists()]


def _expectations(example: Path):
    return sorted((example / "expect").glob("*.rq"))


# --- offline


@pytest.mark.parametrize("example", EXAMPLES, ids=[e.name for e in EXAMPLES])
def test_example_is_well_formed(example):
    problems = []
    for plan in _plans(example):
        check_static(json.loads(plan.read_text()), problems, plan.name)
    assert problems == []


@pytest.mark.parametrize("example", EXAMPLES, ids=[e.name for e in EXAMPLES])
def test_example_writes_only_beneath_its_own_container(example):
    own = WRITTEN_BASE + example.name + "/"
    for plan in _plans(example):
        for target in re.findall(r"https://(?:admin\.)?localhost:4443/[^\"\s<>]*", plan.read_text()):
            assert target in (WRITTEN_BASE,) or target.startswith(own), f"{plan.name}: {target}"


@pytest.mark.parametrize("example", EXAMPLES, ids=[e.name for e in EXAMPLES])
def test_example_has_instruction_and_expectations(example):
    assert (example / "instruction.md").read_text().strip()
    expectations = _expectations(example)
    assert expectations
    for rq in expectations:
        assert parseQuery(rq.read_text())[1].name == "AskQuery", rq.name
    if (example / "result.rq").exists():
        assert parseQuery((example / "result.rq").read_text())[1].name == "SelectQuery"


# --- live


def _base() -> str:
    base = os.getenv("LDH_BASE", WRITTEN_BASE)
    return base if base.endswith("/") else base + "/"


def _rebase(text: str) -> str:
    return text.replace(WRITTEN_BASE, _base())


def _opener():
    cert, password = os.getenv("CERT_PEM_PATH"), os.getenv("CERT_PASSWORD")
    if not (cert and password):
        pytest.skip("CERT_PEM_PATH and CERT_PASSWORD are required to run the examples")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.load_cert_chain(cert, password=password)
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=context)), cert, password


def _request(opener, method, url, headers=None):
    try:
        with opener.open(urllib.request.Request(url, method=method, headers=headers or {})) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _ask(opener, query: str) -> bool:
    url = _base() + "sparql?" + urllib.parse.urlencode({"query": query})
    status, _, body = _request(opener, "GET", url, {"Accept": "application/sparql-results+json"})
    assert status == 200, f"ASK answered {status}: {body[:300]!r}"
    return json.loads(body)["boolean"]


def _remove(opener, container: str) -> None:
    """Delete every document beneath `container`, deepest first."""
    query = (
        "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } "
        f'FILTER(STRSTARTS(STR(?g), "{container}")) }}'
    )
    url = _base() + "sparql?" + urllib.parse.urlencode({"query": query})
    _, _, body = _request(opener, "GET", url, {"Accept": "application/sparql-results+json"})
    graphs = [b["g"]["value"] for b in json.loads(body)["results"]["bindings"]]
    for graph in sorted(graphs, key=len, reverse=True):
        status, headers, _ = _request(opener, "HEAD", graph, {"Accept": "application/n-triples"})
        if status != 200:
            continue
        etag = {k.lower(): v for k, v in headers.items()}.get("etag")
        _request(opener, "DELETE", graph, {"Accept": "application/n-triples", **({"If-Match": etag} if etag else {})})


UPSTREAM_FAILURES = (urllib.error.URLError, TimeoutError, socket.timeout, http.client.RemoteDisconnected, ConnectionError)


@pytest.mark.ldh
@pytest.mark.parametrize("example", EXAMPLES, ids=[e.name for e in EXAMPLES])
def test_example_runs_and_its_expectations_hold(example):
    opener, cert, password = _opener()
    container = _base() + example.name + "/"
    settings = LinkedDataHubSettings(cert_pem_path=cert, cert_password=password)

    _remove(opener, container)
    try:
        for plan in _plans(example):
            try:
                Operation.process_json(settings, json.loads(_rebase(plan.read_text())))
            except UPSTREAM_FAILURES as e:
                pytest.skip(f"{plan.name}: a source did not answer: {e}")
        failed = [rq.name for rq in _expectations(example) if not _ask(opener, _rebase(rq.read_text()))]
        assert failed == []
    finally:
        if not os.getenv("WA_KEEP_EXAMPLES"):
            _remove(opener, container)
