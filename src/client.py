import ssl
import urllib.request
from rdflib import Graph
from http.client import HTTPResponse


class LinkedDataClient:
    def __init__(self, cert_pem_path: str, cert_password: str, verify_ssl: bool = True):
        """
        Initializes the LinkedDataClient with SSL configuration.

        :param cert_pem_path: Path to the certificate .pem file (containing both private key and certificate).
        :param cert_password: Password for the encrypted private key in the .pem file.
        :param verify_ssl: Whether to verify the server's SSL certificate. Default is True.
        """
        self.ssl_context = ssl.create_default_context()

        # Load client certificate
        self.ssl_context.load_cert_chain(certfile=cert_pem_path, password=cert_password)

        # Configure SSL verification
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        # Create an HTTPS handler with the configured SSL context
        self.opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self.ssl_context))

    def get(self, url: str) -> Graph:
        """
        Fetches RDF data from the given URL and returns it as an RDFLib Graph.

        :param url: The URL to fetch RDF data from.
        :return: An RDFLib Graph object containing the parsed RDF data.
        """
        # Set the Accept header to request N-Triples format
        headers = {"Accept": "application/n-triples"}
        request = urllib.request.Request(url, headers=headers)

        # Perform the HTTP request
        response = self.opener.open(request)

        # Read and decode the response data
        data = response.read().decode("utf-8")

        # Parse the N-Triples data into an RDFLib Graph
        g = Graph()
        g.parse(data=data, format="nt")
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
            "Accept": "application/n-triples"
        }
        request = urllib.request.Request(url, data=data.encode("utf-8"), headers=headers, method="POST")

        return self.opener.open(request)

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
            "Accept": "application/n-triples"
        }
        request = urllib.request.Request(url, data=data.encode("utf-8"), headers=headers, method="PUT")

        return self.opener.open(request)

    def delete(self, url: str) -> HTTPResponse:
        """
        Sends an HTTP DELETE request to the given URL.

        :param url: The URL to send the DELETE request to.
        :return: The HTTPResponse object.
        """
        request = urllib.request.Request(url, method="DELETE")

        return self.opener.open(request)
