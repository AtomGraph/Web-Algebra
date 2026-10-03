from typing import Any, ClassVar, Type

from http.client import HTTPResponse
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result
from web_algebra.client import LinkedDataClient, written_url
from web_algebra.focus import report_write
from web_algebra.json_result import JSONResult


class ClientOperation:
    """Mixin that builds an operation's HTTP client from the execution's settings.

    Replaces the `model_post_init` boilerplate that the HTTP-backed operations
    (GET/POST/PUT/PATCH, SELECT/CONSTRUCT/DESCRIBE, ldh-AddFile) each repeated
    verbatim. Subclasses pick the client by overriding ``client_class``
    (``LinkedDataClient`` by default; ``SPARQLClient`` for the query ops,
    ``FileClient`` for the multipart file op).

    All three client classes share the ``(cert_pem_path, cert_password,
    verify_ssl, ca_bundle, recorder)`` constructor, so a single builder covers
    them. Every value comes off ``self.settings``, which is the object one
    execution owns: that is what keeps two executions running concurrently in
    one process from sharing TLS material, or from reporting their writes into
    each other's ``affected_documents``.

    ``verify_ssl`` defaults to off because the command line runs against
    LinkedDataHub's self-signed development certificates; the HTTP service turns
    it back on and names a CA bundle instead.
    """

    client_class: ClassVar[Type] = LinkedDataClient

    def model_post_init(self, __context: Any) -> None:
        self.client = self.client_class(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=getattr(self.settings, "verify_ssl", False),
            ca_bundle=getattr(self.settings, "ca_bundle", None),
            recorder=getattr(self.settings, "recorder", None),
        )

    def written(self, status: int, url: str) -> Result:
        """What a write answered, as its result (formal-semantics.md §4.4): the
        one-row Result of `status` and `url`. The URL is reported to the
        iteration gate of an enclosing ForEach, which refuses one that another
        of its iterations wrote (§3.6)."""
        report_write(self.context, url)
        return JSONResult(
            vars=["status", "url"],
            bindings=[
                {
                    "status": Literal(status, datatype=XSD.integer),
                    "url": URIRef(url),
                }
            ],
        )

    def written_response(self, response: HTTPResponse) -> Result:
        """`written` for an HTTP write response: its `Location` when it has
        one, otherwise the effective request URI."""
        return self.written(response.status, written_url(response))
