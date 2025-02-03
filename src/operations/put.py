from typing import Any
from urllib.parse import quote
import logging
from rdflib import Graph
from client import LinkedDataClient
from operation import Operation

class PUT(Operation):
    """
    Sends RDF data to a specified URL using the HTTP PUT method.

    :attr cert_pem_path: Path to the client certificate PEM file.
    :attr cert_password: Password for the client certificate.
    """

    cert_pem_path: str
    cert_password: str

    def __init__(self,  context: dict = None, url = None, data: str = None):
        """
        Initialize the PUT operation.
        :param url: The JSON operation dict or direct URL string.
        :param data: The JSON operation dict or direct RDF Turtle string.
        :param context: The execution context.
        """
        super().__init__(context)

        if url is None:
            raise ValueError("PUT operation requires 'url' to be set.")
        if data is None:
            raise ValueError("PUT operation requires 'data' to be set.")

        self.url = url  # ✅ Might be a direct URL or a nested operation
        self.data = data  # ✅ Might be a Turtle string or a nested operation

        # ✅ Ensure that credentials are set
        if not hasattr(self, "cert_pem_path") or not hasattr(self, "cert_password"):
            raise ValueError("PUT operation requires 'cert_pem_path' and 'cert_password' to be set.")

        # ✅ Initialize the LinkedDataClient
        self.client = LinkedDataClient(
            cert_pem_path=self.cert_pem_path,
            cert_password=self.cert_password,
            verify_ssl=False  # Optionally disable SSL verification
        )

        logging.info("PUT operation initialized.")

    def execute(self) -> Any:
        """
        Sends RDF data to the specified URL using the HTTP PUT method.
        :return: True if successful, otherwise raises an error.
        """
        logging.info(f"Executing PUT operation with raw URL: {self.url} and data: {self.data}")

        # ✅ Resolve `url` dynamically
        resolved_url = quote(self.resolve_arg(self.url), safe="/:")
        # ✅ Resolve `data` dynamically
        resolved_data = self.resolve_arg(self.data)
        logging.info(f"Resolved URL: {resolved_url}")

        # ✅ Ensure `resolved_data` is parsed as an RDF Graph
        logging.info("Parsing resolved RDF data as Turtle...")
        graph = Graph()
        graph.parse(data=resolved_data, format="turtle")  # ✅ Convert string into RDF Graph

        # ✅ Send PUT request with parsed RDF Graph
        logging.info(f"Sending PUT request to {resolved_url} with RDF data...")
        response = self.client.put(resolved_url, graph)  # ✅ Send RDF Graph
        logging.info(f"PUT operation successful: {response}")

        return True  # ✅ Explicitly return True if successful
