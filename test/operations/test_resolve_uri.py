import pytest
from operations.resolve_uri import ResolveURI

def test_resolve_uri_with_slug():
    print("Testing ResolveURI")
    base = 'http://localhost:80'
    slug = 'foobar'
    expected = base + '/' + slug + '/'
    actual = ResolveURI().execute(base, slug)
    assert actual == expected
