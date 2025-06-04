from typing import Any
import json
import logging
from rdflib import Graph
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from client import LinkedDataClient
from operation import Operation

class PUT(Operation):
    """
    Sends RDF data to a specified URL using the HTTP PUT method.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    def execute(self, arguments: dict[str, Any]) -> bool:
        """
        Sends RDF data to the specified URL using the HTTP PUT method.
        :return: True if successful, otherwise raises an error.
        """
        url: str = arguments["url"]
        data: dict  = arguments["data"]
        
        logging.info(f"Executing PUT operation with URL: %s and data: %s", url, data)

        json_str = json.dumps(data)

        # ✅ Ensure `resolved_data` is parsed as an RDF Graph
        logging.info("Parsing data as JSON-LD...")
        graph = Graph()
        graph.parse(data=json_str, format="json-ld")  # ✅ Convert string into RDF Graph

        # ✅ Send PUT request with parsed RDF Graph
        response = self.client.put(url, graph)  # ✅ Send RDF Graph
        logging.info(f"PUT operation status: {response.status}")

        return response.status < 299

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=str(self.process(arguments)))]
