"""LinkedDataClient sends every write conditionally, DELETE included.

No operation issues a DELETE yet, so formal-semantics.md has nothing to derive
this from; it is a test of the client, outside tests/unit/, and may name it.
"""

from tests.http_stub import StubResponse, default_handler, request_header
from web_algebra.client import LinkedDataClient

DOC = "http://example.org/doc"


def test_delete_sends_the_etag_from_head_as_if_match(http_stub):
    def handler(request):
        if request.get_method() == "HEAD":
            return StubResponse(200, {"ETag": '"abc123"'})
        return default_handler(request)

    http_stub.handler = handler
    LinkedDataClient().delete(DOC)

    [head] = http_stub.with_method("HEAD")
    [delete] = http_stub.with_method("DELETE")
    assert head.full_url == delete.full_url == DOC
    assert request_header(delete, "If-Match") == '"abc123"'
    assert request_header(head, "Accept") == request_header(delete, "Accept")
