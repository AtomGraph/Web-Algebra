"""The ldh-* operations write what LinkedDataHub's CLI writes (formal-semantics.md
Appendix A): each operation and the CLI command it corresponds to are run with
the same inputs, every option included, against a LinkedDataHub, and the two
documents must be the same graph.

Live (marker `ldh`): `LDH_BASE` (default https://localhost:4443/) with the
certificate in CERT_PEM_PATH and CERT_PASSWORD, and `LDH_CLI`, the CLI's
launcher (`cli/bin/ldh` of a LinkedDataHub checkout built with `mvn package`).
Skipped when any is missing. Everything a run writes is deleted afterwards.

Two things the server decides itself are set aside in the comparison: the
dct:created / dct:modified stamps, and the fragment IDs it mints for blank
nodes (`#id<uuid>`), which are compared as blank nodes.
"""

from __future__ import annotations

import os
import re
import ssl
import subprocess
import urllib.error
import urllib.request
import uuid

import pytest
from rdflib import BNode, Graph, URIRef
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.namespace import DCTERMS

from web_algebra.main import LinkedDataHubSettings
from web_algebra.operation import Operation

pytestmark = pytest.mark.ldh

BASE = os.getenv("LDH_BASE", "https://localhost:4443/")
CLI = os.getenv("LDH_CLI")
AC = "https://w3id.org/atomgraph/client#"
SKOLEM = re.compile(r"#id[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
XHTML = '<div xmlns="http://www.w3.org/1999/xhtml"><p>Hello</p></div>'


@pytest.fixture(scope="module")
def ldh():
    cert, password = os.getenv("CERT_PEM_PATH"), os.getenv("CERT_PASSWORD")
    if not (cert and password):
        pytest.skip("CERT_PEM_PATH and CERT_PASSWORD are required")
    if not (CLI and os.access(CLI, os.X_OK)):
        pytest.skip("LDH_CLI must name LinkedDataHub's CLI launcher")
    settings = LinkedDataHubSettings(cert_pem_path=cert, cert_password=password)
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.load_cert_chain(cert, password=password)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    env = {**os.environ, "LDH_CERT_FILE": cert, "LDH_CERT_PASSWORD": password}
    run = BASE + "wa-cli-parity-" + uuid.uuid4().hex[:8] + "/"
    state = {"settings": settings, "opener": opener, "env": env, "run": run}
    yield state
    _delete_under(opener, run)


def _delete_under(opener, prefix):
    """Delete every document under `prefix`, deepest first, each with the
    If-Match LinkedDataHub requires."""
    query = f'SELECT DISTINCT ?g WHERE {{ GRAPH ?g {{ ?s ?p ?o }} FILTER(STRSTARTS(STR(?g), "{prefix}")) }}'
    request = urllib.request.Request(
        BASE + "sparql?" + urllib.parse.urlencode({"query": query}),
        headers={"Accept": "application/sparql-results+xml"},
    )
    with opener.open(request) as response:
        graphs = re.findall(r"<uri>([^<]+)</uri>", response.read().decode())
    accept = {"Accept": "application/n-triples"}
    for graph in sorted(set(graphs), key=lambda u: -u.count("/")):
        try:
            with opener.open(urllib.request.Request(graph, method="HEAD", headers=accept)) as head:
                etag = head.headers["ETag"]
            with opener.open(urllib.request.Request(graph, method="DELETE", headers={**accept, "If-Match": etag})):
                pass
        except urllib.error.HTTPError:
            pass


def _wa(ldh, op, **args):
    plan = {"@op": op, "args": {k: ({"@id": v[1:]} if isinstance(v, str) and v.startswith("@") else v) for k, v in args.items()}}
    return Operation.process_json(ldh["settings"], plan)


def _cli(ldh, *argv) -> str:
    done = subprocess.run([CLI, *argv], env=ldh["env"], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, f"ldh {' '.join(argv[:2])}: {done.stderr.strip()[:500]}"
    return done.stdout.strip()


def _url(result) -> str:
    return str(list(result.bindings)[0]["url"])


def _document(ldh, url) -> Graph:
    request = urllib.request.Request(url, headers={"Accept": "application/n-triples"})
    with ldh["opener"].open(request) as response:
        g = Graph().parse(data=response.read().decode(), format="nt")
    normal = Graph()

    def term(t):
        if isinstance(t, URIRef) and str(t).startswith(url):
            if SKOLEM.search(str(t)):
                return BNode(str(t))
            return URIRef("urn:doc/" + str(t)[len(url):])
        return t

    for s, p, o in g:
        if p in (DCTERMS.created, DCTERMS.modified) and term(s) == URIRef("urn:doc/"):
            continue
        normal.add((term(s), p, term(o)))
    return normal


def _same(ldh, ours, theirs):
    a, b = _document(ldh, ours), _document(ldh, theirs)
    _, only_ours, only_cli = graph_diff(to_isomorphic(a), to_isomorphic(b))
    lines = [f"ours: {t[0].n3()} {t[1].n3()} {t[2].n3()}" for t in only_ours]
    lines += [f"CLI:  {t[0].n3()} {t[1].n3()} {t[2].n3()}" for t in only_cli]
    assert not lines, "\n".join(sorted(lines))


@pytest.fixture(scope="module")
def parent(ldh):
    """The run's container, holding every document the tests write."""
    return _url(_wa(ldh, "ldh-CreateContainer", parent="@" + BASE, title="CLI parity",
                    slug=ldh["run"][len(BASE):-1]))


@pytest.mark.parametrize(
    "options, cli_options",
    [
        ({}, []),
        ({"description": "A container"}, ["--description", "A container"]),
        ({"children_view": False}, ["--no-children-view"]),
        ({"primary_topic": "#this"}, ["--primary-topic", "#this"]),
    ],
    ids=["plain", "description", "no-children-view", "primary-topic"],
)
def test_create_container(ldh, parent, options, cli_options):
    slug = uuid.uuid4().hex[:8]
    ours = _url(_wa(ldh, "ldh-CreateContainer", parent="@" + parent, title="Container", slug=slug, **options))
    theirs = _cli(ldh, "create", "container", "--parent", parent, "--title", "Container", "--slug", slug + "-cli", *cli_options).split()[-1]
    _same(ldh, ours, theirs)


@pytest.mark.parametrize(
    "options, cli_options",
    [
        ({}, []),
        ({"description": "An item"}, ["--description", "An item"]),
        ({"primary_topic": "#this"}, ["--primary-topic", "#this"]),
    ],
    ids=["plain", "description", "primary-topic"],
)
def test_create_item(ldh, parent, options, cli_options):
    slug = uuid.uuid4().hex[:8]
    ours = _url(_wa(ldh, "ldh-CreateItem", container="@" + parent, title="Item", slug=slug, **options))
    theirs = _cli(ldh, "create", "item", "--container", parent, "--title", "Item", "--slug", slug + "-cli", *cli_options).split()[-1]
    _same(ldh, ours, theirs)


@pytest.fixture(scope="module")
def pair(ldh, parent):
    """An item written by the operations and one written by the CLI, which
    the content tests below add the same resources to, in the same order."""
    slug = uuid.uuid4().hex[:8]
    ours = _url(_wa(ldh, "ldh-CreateItem", container="@" + parent, title="Content", slug=slug))
    theirs = _cli(ldh, "create", "item", "--container", parent, "--title", "Content", "--slug", slug + "-cli").split()[-1]
    return ours, theirs


SELECT = "SELECT ?s ?o WHERE { ?s a ?o } LIMIT 10"
CONSTRUCT = "CONSTRUCT { ?s a ?o } WHERE { ?s a ?o } LIMIT 10"

# (operation, its arguments, the CLI command and its options); `{doc}` is the item written to
CONTENT = [
    ("ldh-AddSelect", dict(query=SELECT, title="Q", description="Select", fragment="q", service="@" + BASE + "#service"),
     ["add", "select", "--uri", "#q", "--title", "Q", "--description", "Select", "--query-file", "{select}", "--service", BASE + "#service"]),
    ("ldh-AddConstruct", dict(query=CONSTRUCT, title="C", fragment="c"),
     ["add", "construct", "--uri", "#c", "--title", "C", "--query-file", "{construct}"]),
    ("ldh-AddView", dict(query="@{doc}#q", title="V", description="View", fragment="v", mode="@" + AC + "TableMode"),
     ["add", "view", "--uri", "#v", "--title", "V", "--description", "View", "--query", "{doc}#q", "--mode", AC + "TableMode"]),
    ("ldh-AddResultSetChart", dict(query="@{doc}#q", title="Ch", chart_type="@" + AC + "BarChart", category_var_name="s",
                                   series_var_name=["o", "p"], description="Chart", fragment="ch"),
     ["add", "result-set-chart", "--uri", "#ch", "--title", "Ch", "--query", "{doc}#q", "--chart-type", AC + "BarChart",
      "--category-var-name", "s", "--series-var-name", "o", "--series-var-name", "p", "--description", "Chart"]),
    ("ldh-AddObjectBlock", dict(value="@{doc}#v", title="OB", description="Object", fragment="ob", mode="@" + AC + "GraphMode",
                                graph="@{doc}"),
     ["add", "object-block", "--uri", "#ob", "--title", "OB", "--description", "Object", "--value", "{doc}#v",
      "--mode", AC + "GraphMode", "--graph", "{doc}"]),
    ("ldh-AddXHTMLBlock", dict(value=XHTML, title="XB", description="XHTML", fragment="xb"),
     ["add", "xhtml-block", "--uri", "#xb", "--title", "XB", "--description", "XHTML", "--value", XHTML]),
    ("ldh-AddGenericService", dict(endpoint="@https://example.org/sparql", title="Svc", description="Service", fragment="svc",
                                   graph_store="@https://example.org/service", auth_user="user", auth_pwd="secret"),
     ["add", "generic-service", "--uri", "#svc", "--title", "Svc", "--description", "Service",
      "--endpoint", "https://example.org/sparql", "--graph-store", "https://example.org/service",
      "--auth-user", "user", "--auth-pwd", "secret"]),
]


def test_content(ldh, pair, tmp_path):
    """Each resource added in turn; the documents stay the same at every step."""
    ours, theirs = pair
    files = {"select": tmp_path / "select.rq", "construct": tmp_path / "construct.rq"}
    files["select"].write_text(SELECT)
    files["construct"].write_text(CONSTRUCT)
    for op, args, argv in CONTENT:
        _wa(ldh, op, url="@" + ours, **{k: (v.replace("{doc}", ours) if isinstance(v, str) else v) for k, v in args.items()})
        _cli(ldh, *[a.format(doc=theirs, **files) if "{" in a else a for a in argv], theirs)
        _same(ldh, ours, theirs)

    _wa(ldh, "ldh-RemoveBlock", url="@" + ours, block="@" + ours + "#xb")
    _cli(ldh, "remove", "block", "--block", theirs + "#xb", theirs)
    _same(ldh, ours, theirs)


def test_add_file(ldh, pair, tmp_path):
    ours, theirs = pair
    upload = tmp_path / "upload.txt"
    upload.write_text("Web-Algebra CLI parity " + uuid.uuid4().hex + "\n")
    file_ours = _url(_wa(ldh, "ldh-AddFile", url="@" + ours, file=str(upload), title="Upload", description="A file",
                         content_type="text/plain"))
    file_theirs = _cli(ldh, "add", "file", "--file", str(upload), "--title", "Upload", "--description", "A file",
                       "--content-type", "text/plain", theirs).split()[-1]
    assert file_ours == file_theirs
    _same(ldh, ours, theirs)
