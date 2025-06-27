from typing import Any
import json
import logging
from rdflib import Graph
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.client import LinkedDataClient

class POST(Operation):
    """
    Creates or appends RDF data to a named graph using HTTP POST. The URL serves as both the resource identifier and the named graph address in systems with direct graph identification. Creates or adds to the RDF graph at that URL.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Creates or appends RDF data to a named graph using HTTP POST. The URL serves as both the resource identifier and the named graph address in systems with direct graph identification. Creates or adds to the RDF graph at that URL."
    
    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to send the RDF data to. This should be a valid URL."
                },
                "data": {
                    "type": "object",
                    "description": "The RDF data to append, represented as a JSON-LD dict."
                }
            },
            "required": ["url", "data"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> bool:
        """
        Appends RDF data to the specified URL using the HTTP POST method.
        :param arguments: A dictionary containing:
            - `url`: The URL to send the RDF data to.
            - `data`: The RDF data to append, as a JSON-LD dict.
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

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=str(self.execute(arguments)))]
