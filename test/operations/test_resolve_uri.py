import pytest
import re
from operations.resolve_uri import ResolveURI

def test_resolve_uri_with_slug():
    base = 'http://localhost:80'
    slug = 'foobar'
    expected = base + '/' + slug + '/'
    actual = ResolveURI().execute(base, slug)
    assert actual == expected

def test_resolve_uri_without_slug():
    base = 'http://localhost:80'
    uuid_re = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    uri = ResolveURI().execute(base)
    uuids = re.findall(uuid_re, uri)

    assert uri.startswith(base)
    assert uri.endswith('/')
    assert len(uuids) == 1
