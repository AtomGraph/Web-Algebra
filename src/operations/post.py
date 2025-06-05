from typing import Any
import json
import logging
from rdflib import Graph
from client import LinkedDataClient
from operation import Operation

class POST(Operation):
    """
    Appends RDF data to a specified URL using the HTTP POST method.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    def execute(self, arguments: dict[str, Any]) -> bool:
        """
        Appends RDF data to the specified URL using the HTTP POST method.
        :param arguments: A dictionary containing:
            - `url`: The URL to send the RDF data to.
            - `data`: The RDF data to append, as a Python dict.
        :return: True if successful, otherwise raises an error.
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        data: dict = Operation.execute_json(self.settings, arguments["data"], self.context)
        logging.info(f"Executing PUT operation with URL: %s and data: %s", url, data)

        json_str = json.dumps(data)

        logging.info("Parsing data as JSON-LD...")
        graph = Graph()
        graph.parse(data=json_str, format="json-ld")  # ✅ Convert string into RDF Graph

        response = self.client.post(url, graph)  # ✅ Send RDF Graph
        logging.info("POST operation status: %s", response.status)

        return response.status < 299
