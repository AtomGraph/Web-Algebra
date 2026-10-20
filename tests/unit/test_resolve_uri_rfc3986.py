"""Spec: formal-semantics.md §4.2 ResolveURI - RFC 3986 §5.2 reference
resolution, for a base of any scheme; an absolute reference has its dot
segments removed; the base's scheme is never dropped.

Expected values: RFC 3986 §5.4.1/§5.4.2 examples (base http://a/b/c/d;p?q)
and the §5.2 algorithm applied by hand to non-hierarchical bases.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef

from web_algebra.operation import Operation

RFC_BASE = "http://a/b/c/d;p?q"


def _resolve(settings, base, relative):
    result = Operation.process_json(
        settings, {"@op": "ResolveURI", "args": {"base": {"@id": base}, "relative": relative}}
    )
    assert isinstance(result, URIRef)
    return str(result)


@pytest.mark.parametrize(
    "relative, expected",
    [
        # §5.4.1 normal examples
        ("g:h", "g:h"),
        ("g", "http://a/b/c/g"),
        ("./g", "http://a/b/c/g"),
        ("g/", "http://a/b/c/g/"),
        ("/g", "http://a/g"),
        ("//g", "http://g"),
        ("?y", "http://a/b/c/d;p?y"),
        ("g?y", "http://a/b/c/g?y"),
        ("#s", "http://a/b/c/d;p?q#s"),
        ("g#s", "http://a/b/c/g#s"),
        (";x", "http://a/b/c/;x"),
        ("", "http://a/b/c/d;p?q"),
        (".", "http://a/b/c/"),
        ("./", "http://a/b/c/"),
        ("..", "http://a/b/"),
        ("../g", "http://a/b/g"),
        ("../..", "http://a/"),
        ("../../g", "http://a/g"),
        # §5.4.2 abnormal examples
        ("../../../g", "http://a/g"),
        ("../../../../g", "http://a/g"),
        ("/./g", "http://a/g"),
        ("/../g", "http://a/g"),
        ("g.", "http://a/b/c/g."),
        (".g", "http://a/b/c/.g"),
        ("./../g", "http://a/b/g"),
        ("./g/.", "http://a/b/c/g/"),
        ("g/./h", "http://a/b/c/g/h"),
        ("g/../h", "http://a/b/c/h"),
        ("g;x=1/./y", "http://a/b/c/g;x=1/y"),
        ("g;x=1/../y", "http://a/b/c/y"),
        ("g?y/./x", "http://a/b/c/g?y/./x"),
        ("g#s/../x", "http://a/b/c/g#s/../x"),
        ("http:g", "http:g"),
    ],
)
def test_rfc3986_examples(settings, relative, expected):
    assert _resolve(settings, RFC_BASE, relative) == expected


@pytest.mark.parametrize(
    "base, relative, expected",
    [
        ("urn:a:b", "#f", "urn:a:b#f"),
        ("urn:a:b", "c", "urn:c"),
        ("urn:a:b", "?q", "urn:a:b?q"),
        ("urn:isbn:0451450523", "foo", "urn:foo"),
        ("tag:ex.org,2024:a/b", "c", "tag:ex.org,2024:a/c"),
        ("tag:ex.org,2024:a/b", "../c", "tag:/c"),  # §5.2.4: ".." removes the rootless first segment
        ("mailto:a@ex.org", "b@ex.org", "mailto:b@ex.org"),
        ("custom://h/x/y", "z", "custom://h/x/z"),
        ("custom://h/x/y", "../z", "custom://h/z"),
    ],
)
def test_any_scheme_keeps_the_base_scheme(settings, base, relative, expected):
    assert _resolve(settings, base, relative) == expected


def test_an_absolute_reference_has_its_dot_segments_removed(settings):
    assert _resolve(settings, RFC_BASE, "http://x/a/../b/./c") == "http://x/b/c"
