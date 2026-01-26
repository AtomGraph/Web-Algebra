from typing import Optional
import ssl
import json
import logging
import time
import urllib.request
import urllib.error
from email.utils import parsedate_to_datetime
from http.client import HTTPResponse
from rdflib import Graph
from rdflib.plugins.sparql.parser import parseQuery


MEDIA_TYPES = {
    "application/n-triples": "nt",
    "text/turtle": "turtle",
    "application/ld+json": "json-ld",
    "application/rdf+xml": "xml",
}


class HTTPRedirectHandler308(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Handle 308 Permanent Redirect by preserving method and body"""
        if code == 308:
            return urllib.request.Request(
                newurl, data=req.data, headers=req.headers, method=req.get_method()
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class LinkedDataClient:
    def __init__(
        self,
        cert_pem_path: Optional[str] = None,
        cert_password: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        """
        Initializes the LinkedDataClient with SSL configuration.

        :param cert_pem_path: Path to the certificate .pem file (containing both private key and certificate).
        :param cert_password: Password for the encrypted private key in the .pem file.
        :param verify_ssl: Whether to verify the server's SSL certificate. Default is True.
        """
        # Always create SSL context
        self.ssl_context = ssl.create_default_context()

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
        )

        # Add proper User-Agent header for external services like Wikidata
        self.opener.addheaders = [
            (
                "User-Agent",
                "Web-Algebra/1.0 (LinkedData Processing System; https://github.com/atomgraph/Web-Algebra)",
            )
        ]

    def _request_with_retry(self, request: urllib.request.Request, max_retries: int = 5) -> HTTPResponse:
        """
        Execute HTTP request with automatic retry on 429 (Too Many Requests) responses.

        Respects the Retry-After header if present, otherwise uses exponential backoff.
        All other HTTP errors are raised immediately without retry.

        :param request: The urllib Request object to execute
        :param max_retries: Maximum number of retry attempts (default 5)
        :return: HTTPResponse object on success
        :raises: urllib.error.HTTPError for non-429 errors or after max retries
        """
        attempt = 0

        while attempt <= max_retries:
            try:
                return self.opener.open(request)
            except urllib.error.HTTPError as e:
                # Only retry on 429 (Too Many Requests)
                if e.code != 429:
                    raise

                # Check if we've exhausted retries
                if attempt >= max_retries:
                    logging.error(f"Max retries ({max_retries}) exceeded for {request.full_url}")
                    raise

                # Parse Retry-After header
                retry_after = e.headers.get('Retry-After')
                if retry_after:
                    try:
                        # Try parsing as seconds (integer)
                        wait_time = int(retry_after)
                    except ValueError:
                        # Try parsing as HTTP-date
                        try:
                            retry_date = parsedate_to_datetime(retry_after)
                            wait_time = (retry_date - parsedate_to_datetime(time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))).total_seconds()
                            wait_time = max(0, wait_time)  # Ensure non-negative
                        except Exception:
                            # Fallback to exponential backoff if parsing fails
                            wait_time = min(1 * (2 ** attempt), 60)
                else:
                    # No Retry-After header, use exponential backoff
                    wait_time = min(1 * (2 ** attempt), 60)

                attempt += 1
                logging.warning(f"HTTP 429 received for {request.full_url}. Retry {attempt}/{max_retries} after {wait_time:.1f} seconds")
                time.sleep(wait_time)

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

        # Perform the HTTP request with retry on 429
        response = self._request_with_retry(request)

        # Read and decode the response data
        data = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type").split(";")[0]
        rdf_format = MEDIA_TYPES.get(content_type)
        if not rdf_format:
            raise ValueError(
                f"Unsupported Content-Type: {content_type}. Supported types are: {', '.join(MEDIA_TYPES.keys())}"
            )

        # Parse the RDF data into an RDFLib Graph
        g = Graph()
        g.parse(data=data, format=rdf_format, publicID=url)
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
        request = urllib.request.Request(
            url, data=data.encode("utf-8"), headers=headers, method="POST"
        )

        return self._request_with_retry(request)

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
        request = urllib.request.Request(
            url, data=data.encode("utf-8"), headers=headers, method="PUT"
        )

        return self._request_with_retry(request)

    def delete(self, url: str) -> HTTPResponse:
        """
        Sends an HTTP DELETE request to the given URL.

        :param url: The URL to send the DELETE request to.
        :return: The HTTPResponse object.
        """
        request = urllib.request.Request(url, method="DELETE")

        return self._request_with_retry(request)

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
        request = urllib.request.Request(
            url, data=sparql_update.encode("utf-8"), headers=headers, method="PATCH"
        )

        return self._request_with_retry(request)


class SPARQLClient:
    def __init__(
        self,
        cert_pem_path: Optional[str] = None,
        cert_password: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        """
        Initializes the SPARQLClient with optional SSL certificate.

        :param cert_pem_path: Path to .pem file containing cert+key
        :param cert_password: Password for the PEM file
        :param verify_ssl: Whether to verify server SSL certificate
        """
        # Always create SSL context
        self.ssl_context = ssl.create_default_context()

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
            urllib.request.HTTPSHandler(context=self.ssl_context)
        )

        # Add proper User-Agent header for external services like Wikidata
        self.opener.addheaders = [
            (
                "User-Agent",
                "Web-Algebra/1.0 (LinkedData Processing System; https://github.com/atomgraph/Web-Algebra)",
            )
        ]

    def query(self, endpoint_url: str, query_string: str) -> dict:
        """
        Executes a SPARQL query. Returns Graph for CONSTRUCT/DESCRIBE, Result for SELECT/ASK.

        :param endpoint_url: The SPARQL endpoint URL
        :param query_string: SPARQL query string
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

        # Encode URL parameters
        params = urllib.parse.urlencode({"query": query_string})
        url = f"{endpoint_url}?{params}"
        headers = {"Accept": accept}

        request = urllib.request.Request(url, headers=headers)
        response = self.opener.open(request)
        data = response.read()

        if accept == "application/n-triples":
            g = Graph()
            # convert N-Triples to JSON-LD
            g.parse(data=data.decode("utf-8"), format="nt")
            jsonld_str = g.serialize(format="json-ld")
            jsonld_data = json.loads(jsonld_str)
            return jsonld_data
        else:
            # return SPARQL JSON results as a dict
            return json.loads(data.decode("utf-8"))
