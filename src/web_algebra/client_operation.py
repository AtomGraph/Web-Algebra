from typing import Any, ClassVar, Type

from web_algebra.client import LinkedDataClient


class ClientOperation:
    """Mixin that builds an operation's HTTP client from the cert settings.

    Replaces the `model_post_init` boilerplate that the HTTP-backed operations
    (GET/POST/PUT/PATCH, SELECT/CONSTRUCT/DESCRIBE, ldh-AddFile) each repeated
    verbatim. Subclasses pick the client by overriding ``client_class``
    (``LinkedDataClient`` by default; ``SPARQLClient`` for the query ops,
    ``FileClient`` for the multipart file op).

    All three client classes share the ``(cert_pem_path, cert_password,
    verify_ssl)`` constructor, so a single builder covers them. ``verify_ssl``
    is off to match LinkedDataHub's self-signed development certificates.
    """

    client_class: ClassVar[Type] = LinkedDataClient

    def model_post_init(self, __context: Any) -> None:
        self.client = self.client_class(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,
        )
