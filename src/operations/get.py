import json
import logging
from rdflib import Graph
from typing import Any, Union
from operation import Operation
from client import LinkedDataClient

class GET(Operation):
    """
    Fetch RDF data from a given URL and return it as a Python dict of JSON-LD.

    :attr cert_pem_path: Path to the client certificate PEM file.
    :attr cert_password: Password for the client certificate.
    """

    cert_pem_path: str
    cert_password: str

    def __init__(self, context: dict = None, url: Union[str, dict] = None):
        """
        Initialize the GET operation.
        :param context: Execution context.
        :param url: The JSON operation dict or direct URL string.
        """
        super().__init__(context)

        if url is None:
            raise ValueError("GET operation requires 'url' to be set.")

        self.url = url  # May be a direct string or a nested operation

        # Ensure that credentials are set
        if not hasattr(self, "cert_pem_path") or not hasattr(self, "cert_password"):
            raise ValueError("GET operation requires 'cert_pem_path' and 'cert_password' to be set.")

        # Initialize the LinkedDataClient
        self.client = LinkedDataClient(
            cert_pem_path=self.cert_pem_path,
            cert_password=self.cert_password,
            verify_ssl=False  # Optionally disable SSL verification
        )

        logging.info("GET operation initialized.")

    def execute(self) -> dict:
        """
        Fetch RDF data from the specified URL and return a Python dict representing JSON-LD.
        :return: A Python dict of JSON-LD data from the resolved URL.
        """
        logging.info(f"Executing GET operation with raw URL: {self.url}")

        # 1) Resolve `url` dynamically
        resolved_url = self.resolve_arg(self.url)
        if not isinstance(resolved_url, str):
            raise ValueError("GET operation expects 'url' to resolve to a string.")
        logging.info(f"Resolved URL: {resolved_url}")

        # 2) Fetch RDF graph from the resolved URL
        logging.info(f"Fetching RDF data from {resolved_url}...")
        graph: Graph = self.client.get(resolved_url)  # Let exceptions propagate
        logging.info(f"Successfully fetched RDF data from {resolved_url}.")

        # 3) Serialize the graph to JSON-LD (string)
        jsonld_str = graph.serialize(format="json-ld")

        # 4) Convert that string to a Python dict
        jsonld_data = json.loads(jsonld_str)

        logging.info("Returning RDF data as a Python dict of JSON-LD.")
        return jsonld_data
