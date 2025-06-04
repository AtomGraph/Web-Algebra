from typing import Any, ClassVar, Dict
import logging
from rdflib import Graph
from client import LinkedDataClient
from operation import Operation

class POST(Operation):
    """
    Appends RDF data to a specified URL using the HTTP POST method.

    :attr cert_pem_path: Path to the client certificate PEM file.
    :attr cert_password: Password for the client certificate.
    """

    url: str  # Can be a direct URL string or a nested operation
    data: Dict # Can be a JSON-LD dict or a nested operation

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    def execute(self) -> bool:
        """
        Appends RDF data to the specified URL using the HTTP POST method.
        :return: True if successful, otherwise raises an error.
        """
        logging.info(f"Executing POST operation with raw URL: {self.url} and data: {self.data}")

        # ✅ Resolve `url` dynamically
        resolved_url = self.resolve_arg(self.url)
        # ✅ Resolve `data` dynamically
        resolved_data = self.resolve_arg(self.data)
        logging.info(f"Resolved URL: {resolved_url}")

        # ✅ Ensure `resolved_data` is parsed as an RDF Graph
        logging.info("Parsing resolved RDF data as Turtle...")
        graph = Graph()
        graph.parse(data=resolved_data, format="turtle")  # ✅ Convert string into RDF Graph

        # ✅ Send POST request with parsed RDF Graph
        logging.info(f"Sending POST request to {resolved_url} with RDF data...")
        response = self.client.post(resolved_url, graph)  # ✅ Send RDF Graph
        logging.info(f"POST operation status: {response.status}")

        return response.status < 299
