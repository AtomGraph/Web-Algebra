from typing import Optional, Protocol, Tuple
import hashlib
import ssl
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPResponse
from rdflib import Graph
from rdflib.plugins.sparql.parser import parseQuery
from urllib3.filepost import encode_multipart_formdata
from web_algebra.exceptions import WriteRefusedError


MEDIA_TYPES = {
    "application/n-triples": "nt",
    "text/turtle": "turtle",
    "application/ld+json": "json-ld",
    "application/rdf+xml": "xml",
}

# HTTP methods that change the resource they address. A client reports each one
# it completes to its recorder, and that report is the only source of an
# execution's `affected_documents` — derived from what was actually sent, not
# from reading the plan, so an operation that writes somewhere the plan does not
# name outright (a `ForEach` body resolving its URL per row) is still accounted
# for.
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class WriteRecorder(Protocol):
    """What a client needs of the execution it is running inside.

    Kept to one method so `client.py` stays free of any dependency on the
    service layer: the CLI passes nothing and the clients record nowhere.
    """

    def record(self, method: str, url: str) -> None: ...


class HTTPRedirectHandler308(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Handle 308 Permanent Redirect by preserving method and body"""
        if code == 308:
            return urllib.request.Request(
                newurl, data=req.data, headers=req.headers, method=req.get_method()
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RetryAfterHandler(urllib.request.BaseHandler):
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._retry_counts: dict = {}

    def http_error_429(self, req, fp, code, msg, hdrs):
        key = req.full_url
        count = self._retry_counts.get(key, 0)
        if count >= self.max_retries:
            self._retry_counts.pop(key, None)
            raise urllib.error.HTTPError(req.full_url, code, msg, hdrs, fp)
        self._retry_counts[key] = count + 1
        retry_after = hdrs.get("Retry-After", "1")
        try:
            delay = float(retry_after)
        except ValueError:
            retry_dt = parsedate_to_datetime(retry_after)
            delay = max(0.0, (retry_dt - datetime.now(tz=timezone.utc)).total_seconds())
        time.sleep(delay)
        return self.parent.open(req)


def send(
    opener: urllib.request.OpenerDirector,
    request: urllib.request.Request,
    recorder: Optional[WriteRecorder] = None,
) -> HTTPResponse:
    """Open `request`; a mutating one answered outside 2xx raises
    `WriteRefusedError` (formal-semantics.md §4.4), and one that succeeded is
    reported to `recorder`."""
    method = request.get_method()
    try:
        response = opener.open(request)
    except urllib.error.HTTPError as e:
        if method not in MUTATING_METHODS:
            raise
        raise WriteRefusedError(method, request.full_url, e.code, http_reason(e)) from None
    if method in MUTATING_METHODS and not 200 <= response.status < 300:
        raise WriteRefusedError(method, request.full_url, response.status, response.reason)
    if recorder is not None and method in MUTATING_METHODS:
        recorder.record(method, written_url(response))
    return response


def http_reason(error: urllib.error.HTTPError) -> str:
    """What a server said when it refused a request, cut to a sentence or so:
    the body when it is text, otherwise the status line's reason phrase."""
    content_type = (error.headers.get("Content-Type") or "") if error.headers else ""
    textual = content_type.startswith("text/") or any(
        marker in content_type for marker in ("json", "xml", "n-triples", "turtle")
    )
    if textual:
        try:
            body = " ".join(error.read().decode("utf-8", "replace").split())
        except Exception:
            body = ""
        if body:
            return body if len(body) <= 400 else body[:400] + "…"
    return str(error.reason)


def written_url(response: HTTPResponse) -> str:
    """The URI of the resource a write produced (formal-semantics.md §4.4):
    the response's `Location` when it has one — resolved against the request,
    as a relative reference may be — otherwise the effective request URI."""
    location = response.headers.get("Location") if response.headers else None
    if location:
        return urllib.parse.urljoin(response.geturl(), location)
    return response.geturl()


class LinkedDataClient:
    def __init__(
        self,
        cert_pem_path: Optional[str] = None,
        cert_password: Optional[str] = None,
        verify_ssl: bool = True,
        ca_bundle: Optional[str] = None,
        recorder: Optional[WriteRecorder] = None,
    ):
        """
        Initializes the LinkedDataClient with SSL configuration.

        :param cert_pem_path: Path to the certificate .pem file (containing both private key and certificate).
        :param cert_password: Password for the encrypted private key in the .pem file.
        :param verify_ssl: Whether to verify the server's SSL certificate. Default is True.
        :param ca_bundle: Path to a CA bundle that verification trusts in addition to the
            system store — how a self-signed LinkedDataHub is reached with verification left on.
        :param recorder: Receives every completed mutating request, or None to record nowhere.
        """
        self.recorder = recorder
        # Always create SSL context
        self.ssl_context = ssl.create_default_context(cafile=ca_bundle)

        # Load client certificate if provided
        if cert_pem_path and cert_password:
            self.ssl_context.load_cert_chain(
                certfile=cert_pem_path, password=cert_password
            )

        # Configure SSL verification
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        # Create an HTTPS handler with the configured SSL context
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self.ssl_context),
            HTTPRedirectHandler308(),
            RetryAfterHandler(),
        )

        # Add proper User-Agent header for external services like Wikidata
        self.opener.addheaders = [
            (
                "User-Agent",
                "Web-Algebra/1.0 (LinkedData Processing System; https://github.com/atomgraph/Web-Algebra)",
            )
        ]

    def _send(self, request: urllib.request.Request) -> HTTPResponse:
        """Open a request, reporting it to the recorder when it changed something.

        Reported *after* the response arrives and against the response's own URL,
        so a request that raised is not recorded as a change and a redirected one
        is recorded where the write actually landed.

        A write answered outside 2xx is refused (formal-semantics.md §4.4) and
        raises `WriteRefusedError` with the status and the server's reason; a
        read answered so is a transport failure and propagates unwrapped (§3.7).
        """
        return send(self.opener, request, self.recorder)

    def conditional(self, url: str, accept: str) -> dict:
        """The headers a write to `url` carries: `If-Match` with the resource's
        current entity tag, when it has one (formal-semantics.md §4.4).

        A server that applies a write as read-modify-write (LinkedDataHub)
        requires a write to an existing document to be conditional, and answers
        428 without. The tag is read by HEAD with the `Accept` the write itself
        sends, since it names a negotiated variant. A resource that does not
        exist, or cannot be read, has no tag and is written unconditionally.
        """
        request = urllib.request.Request(url, headers={"Accept": accept}, method="HEAD")
        try:
            response = self.opener.open(request)
        except Exception:
            # a resource that cannot be read cannot be matched against; the
            # write answers for itself
            return {}
        try:
            etag = response.headers.get("ETag")
        finally:
            response.close()
        return {"If-Match": etag} if etag else {}

    def get(self, url: str) -> Graph:
        """
        Fetches RDF data from the given URL and returns it as an RDFLib Graph.

        :param url: The URL to fetch RDF data from.
        :return: An RDFLib Graph object containing the parsed RDF data.
        """
        # Set the Accept header
        accept_header = ", ".join(MEDIA_TYPES.keys())
        headers = {"Accept": accept_header}
        request = urllib.request.Request(url, headers=headers)

        # Perform the HTTP request
        response = self.opener.open(request)

        # Read and decode the response data
        data = response.read().decode("utf-8")
        # Non-RDF responses are errors (formal-semantics.md §4.4): the
        # Linked Data operations read and write RDF graphs only.
        content_type_header = response.headers.get("Content-Type")
        content_type = (
            content_type_header.split(";")[0].strip() if content_type_header else None
        )
        rdf_format = MEDIA_TYPES.get(content_type)
        if not rdf_format:
            raise ValueError(
                f"Non-RDF response from {url}: Content-Type {content_type!r} is not "
                f"an RDF media type (supported: {', '.join(MEDIA_TYPES.keys())})"
            )

        # Parse the RDF data into an RDFLib Graph
        g = Graph()
        try:
            g.parse(data=data, format=rdf_format, publicID=url)
        except Exception as e:
            raise ValueError(
                f"Non-RDF response from {url}: body does not parse as {content_type}: {e}"
            ) from None
        return g

    def post(self, url: str, graph: Graph) -> HTTPResponse:
        """
        Sends RDF data to the given URL using HTTP POST.

        :param url: The URL to send RDF data to.
        :param data: An RDFLib Graph containing the data to send.
        :return: The HTTPResponse object.
        """
        # Serialize the RDF data to N-Triples
        data = graph.serialize(format="nt")
        headers = {
            "Content-Type": "application/n-triples",
            "Accept": "application/n-triples",
        }
        headers.update(self.conditional(url, headers["Accept"]))
        request = urllib.request.Request(
            url, data=data.encode("utf-8"), headers=headers, method="POST"
        )

        return self._send(request)

    def put(self, url: str, graph: Graph) -> HTTPResponse:
        """
        Sends RDF data to the given URL using HTTP PUT.

        :param url: The URL to send RDF data to.
        :param data: An RDFLib Graph containing the data to send.
        :return: The HTTPResponse object.
        """
        # Serialize the RDF data to N-Triples
        data = graph.serialize(format="nt")
        headers = {
            "Content-Type": "application/n-triples",
            "Accept": "application/n-triples",
        }
        headers.update(self.conditional(url, headers["Accept"]))
        request = urllib.request.Request(
            url, data=data.encode("utf-8"), headers=headers, method="PUT"
        )

        return self._send(request)

    def delete(self, url: str) -> HTTPResponse:
        """
        Sends an HTTP DELETE request to the given URL.

        :param url: The URL to send the DELETE request to.
        :return: The HTTPResponse object.
        """
        request = urllib.request.Request(url, method="DELETE")

        return self._send(request)

    def patch(self, url: str, sparql_update: str) -> HTTPResponse:
        """
        Sends a SPARQL UPDATE query to the given URL using HTTP PATCH.

        :param url: The URL to send the SPARQL UPDATE to.
        :param sparql_update: The SPARQL UPDATE query string.
        :return: The HTTPResponse object.
        """
        headers = {
            "Content-Type": "application/sparql-update",
            "Accept": "application/n-triples",
        }
        headers.update(self.conditional(url, headers["Accept"]))
        request = urllib.request.Request(
            url, data=sparql_update.encode("utf-8"), headers=headers, method="PATCH"
        )

        return self._send(request)


class FileClient:
    """Multipart RDF/POST file upload for LinkedDataHub file resources.

    Files are not Linked Data — request bodies are bytes with a Content-Type
    rather than RDF graphs — so they get their own client surface instead
    of being grafted onto `LinkedDataClient`. Auth and TLS setup duplicate
    `LinkedDataClient` / `SPARQLClient` by convention: each client in this
    module configures its own ssl_context + opener inline.

    Wire format matches LinkedDataHub's `bin/add-file.sh` script: a
    multipart/form-data body using LDH's RDF/POST dialect where each
    `pu=<predicate>` form field is paired with the next `ol=<literal>` or
    `ou=<uri>` field, sharing a blank-node subject named via `sb=`. The
    file body itself is carried as a multipart file part labelled `ol`
    with the supplied Content-Type. LDH stores the bytes under its
    built-in `/uploads/{sha1}` namespace and appends the file's RDF
    description (filename, MIME type, sha1, title) to the target document.
    """

    _NFO_FILE_NAME = "http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#fileName"
    _NFO_FILE_DATA_OBJECT = "http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#FileDataObject"
    _DCT_TITLE = "http://purl.org/dc/terms/title"
    _DCT_DESCRIPTION = "http://purl.org/dc/terms/description"
    _RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

    def __init__(
        self,
        cert_pem_path: Optional[str] = None,
        cert_password: Optional[str] = None,
        verify_ssl: bool = True,
        ca_bundle: Optional[str] = None,
        recorder: Optional[WriteRecorder] = None,
    ):
        """Initialize TLS context + opener; mirrors `LinkedDataClient.__init__`."""
        self.recorder = recorder
        self.ssl_context = ssl.create_default_context(cafile=ca_bundle)

        if cert_pem_path and cert_password:
            self.ssl_context.load_cert_chain(
                certfile=cert_pem_path, password=cert_password
            )

        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self.ssl_context),
            HTTPRedirectHandler308(),
            RetryAfterHandler(),
        )

        self.opener.addheaders = [
            (
                "User-Agent",
                "Web-Algebra/1.0 (LinkedData Processing System; https://github.com/atomgraph/Web-Algebra)",
            )
        ]

    def add_file(
        self,
        target_url: str,
        file_body: bytes,
        content_type: str,
        title: str,
        description: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Tuple[HTTPResponse, str]:
        """RDF/POST a file to `target_url`.

        :param target_url: The document URI the file's RDF description is
            appended to. Note this is *not* the URI the file ends up at —
            LDH stores the bytes under its own `/uploads/{sha1}` namespace
            regardless of `target_url`.
        :param file_body: Raw file bytes.
        :param content_type: MIME type of the file (e.g. `image/png`).
        :param title: `dct:title` literal.
        :param description: Optional `dct:description` literal.
        :param filename: Optional filename for the multipart part's
            `Content-Disposition`. Defaults to `"upload"` when absent;
            LDH does not depend on this value for URI minting.
        :return: `(HTTPResponse, sha1_hex)`. The sha1 is computed over
            `file_body` client-side so callers can construct the resulting
            `<base>/uploads/{sha1}` URI without parsing the response body.
        """
        sha1 = hashlib.sha1(file_body).hexdigest()

        # `encode_multipart_formdata` accepts a list of `(name, value)`
        # tuples — duplicates allowed, order preserved. A plain string/bytes
        # value becomes a form field; a `(filename, body, content_type)`
        # tuple becomes a file part. RDF/POST relies on this ordering
        # because each `pu=<predicate>` field is paired with the next
        # `ol=<literal>` / `ou=<uri>` field by LDH's parser.
        fields: list[tuple[str, object]] = [
            ("rdf", ""),
            ("sb", "file"),
            ("pu", self._NFO_FILE_NAME),
            ("ol", (filename or "upload", file_body, content_type)),
            ("pu", self._DCT_TITLE),
            ("ol", title),
            ("pu", self._RDF_TYPE),
            ("ou", self._NFO_FILE_DATA_OBJECT),
        ]
        if description:
            fields.extend([
                ("pu", self._DCT_DESCRIPTION),
                ("ol", description),
            ])

        body, content_type_header = encode_multipart_formdata(fields)
        headers = {
            "Content-Type": content_type_header,
            "Accept": "text/turtle",
        }
        request = urllib.request.Request(
            target_url, data=body, headers=headers, method="POST"
        )
        response = send(self.opener, request, self.recorder)
        return response, sha1


class SPARQLClient:
    def __init__(
        self,
        cert_pem_path: Optional[str] = None,
        cert_password: Optional[str] = None,
        verify_ssl: bool = True,
        ca_bundle: Optional[str] = None,
        recorder: Optional[WriteRecorder] = None,
    ):
        """
        Initializes the SPARQLClient with optional SSL certificate.

        :param cert_pem_path: Path to .pem file containing cert+key
        :param cert_password: Password for the PEM file
        :param verify_ssl: Whether to verify server SSL certificate
        :param ca_bundle: Path to an extra CA bundle verification trusts
        :param recorder: Unused here — queries read; the parameter keeps the three
            clients' constructor uniform so `ClientOperation` builds any of them the same way.
        """
        self.recorder = recorder
        # Always create SSL context
        self.ssl_context = ssl.create_default_context(cafile=ca_bundle)

        # Load client certificate if provided
        if cert_pem_path and cert_password:
            self.ssl_context.load_cert_chain(
                certfile=cert_pem_path, password=cert_password
            )

        # Configure SSL verification
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self.ssl_context),
            RetryAfterHandler(),
        )

        # Add proper User-Agent header for external services like Wikidata
        self.opener.addheaders = [
            (
                "User-Agent",
                "Web-Algebra/1.0 (LinkedData Processing System; https://github.com/atomgraph/Web-Algebra)",
            )
        ]

    def query(self, endpoint_url: str, query_string: str, post: bool = False) -> dict:
        """
        Executes a SPARQL query. Returns Graph for CONSTRUCT/DESCRIBE, Result for SELECT/ASK.

        :param endpoint_url: The SPARQL endpoint URL
        :param query_string: SPARQL query string
        :param post: Send the query as a form POST (SPARQL 1.1 Protocol §2.1.2) —
            for a query too long for a URL, such as one scoped by a VALUES block
        :return: rdflib.Graph or rdflib.query.Result
        """
        parsed = parseQuery(query_string)
        query_type = parsed[1].name  # e.g., 'SelectQuery', 'ConstructQuery'

        if query_type in {"SelectQuery", "AskQuery"}:
            accept = "application/sparql-results+json"
        elif query_type in {"ConstructQuery", "DescribeQuery"}:
            accept = "application/n-triples"
        else:
            raise ValueError(f"Unsupported query type: {query_type}")

        headers = {"Accept": accept}
        if post:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            request = urllib.request.Request(
                endpoint_url,
                data=urllib.parse.urlencode({"query": query_string}).encode("utf-8"),
                headers=headers,
                method="POST",
            )
        else:
            # Encode URL parameters
            params = urllib.parse.urlencode({"query": query_string})
            request = urllib.request.Request(f"{endpoint_url}?{params}", headers=headers)
        response = self.opener.open(request)
        data = response.read()

        if accept == "application/n-triples":
            g = Graph()
            # convert N-Triples to JSON-LD; a body that does not parse as the
            # negotiated format is an error (formal-semantics.md §4.3)
            try:
                g.parse(data=data.decode("utf-8"), format="nt")
            except Exception as e:
                raise ValueError(
                    f"Non-RDF response from {endpoint_url}: body does not parse "
                    f"as N-Triples: {e}"
                ) from None
            jsonld_str = g.serialize(format="json-ld")
            jsonld_data = json.loads(jsonld_str)
            return jsonld_data
        else:
            # SPARQL JSON results as a dict; json.JSONDecodeError is a
            # ValueError subclass, satisfying the §4.3 error contract
            return json.loads(data.decode("utf-8"))

    def takes_graph(self, endpoint_url: str) -> bool:
        """Whether `endpoint_url` takes `GRAPH` in a query, asked once per
        endpoint with `ASK { GRAPH ?g { ?s ?p ?o } }` and remembered for the
        process. Blazegraph in triples mode (Wikidata's) refuses any query with
        `GRAPH` as malformed: a 4xx says no, anything else says yes and leaves
        the real query to report what is wrong."""
        if endpoint_url not in _TAKES_GRAPH:
            try:
                self.query(endpoint_url, "ASK { GRAPH ?g { ?s ?p ?o } }", post=True)
                _TAKES_GRAPH[endpoint_url] = True
            except urllib.error.HTTPError as e:
                _TAKES_GRAPH[endpoint_url] = not 400 <= e.code < 500
            except Exception:
                _TAKES_GRAPH[endpoint_url] = True
        return _TAKES_GRAPH[endpoint_url]


# Endpoints by whether they take GRAPH in a query (`SPARQLClient.takes_graph`).
_TAKES_GRAPH: dict = {}
