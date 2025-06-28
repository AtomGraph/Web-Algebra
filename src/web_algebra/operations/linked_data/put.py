from typing import Any
import json
import logging
from urllib.error import HTTPError
from rdflib import Graph
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.client import LinkedDataClient

class PUT(Operation):
    """
    Replaces RDF data in a named graph using HTTP PUT. The URL serves as both the resource identifier and the named graph address in systems with direct graph identification. Completely replaces the RDF graph at that URL.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Replaces RDF data in a named graph using HTTP PUT. The URL serves as both the resource identifier and the named graph address in systems with direct graph identification. Completely replaces the RDF graph at that URL."
    
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
                    "description": "The RDF data to send, represented as a JSON-LD dict."
                }
            },
            "required": ["url", "data"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> bool:
        """
        Sends RDF data to the specified URL using the HTTP PUT method.
        :param arguments: A dictionary containing:
            - `url`: The URL to send the RDF data to.
            - `data`: The RDF data to send, represented as a JSON-LD dict.
        :return: True if successful, otherwise raises an error. The second return value is the URL of the created document.
        """
        url = Operation.execute_json(self.settings, arguments["url"], self.context)
        data = Operation.execute_json(self.settings, arguments["data"], self.context)
        
        logging.info("Executing PUT operation with URL: %s", url)

        json_str = json.dumps(data)

        logging.info("Parsing data as JSON-LD...")
        graph = Graph()
        graph.parse(data=json_str, format="json-ld")  # ✅ Convert string into RDF Graph

        # ✅ Send PUT request with parsed RDF Graph
        response = self.client.put(url, graph)  # ✅ Send RDF Graph
        logging.info("PUT operation status: %s", response.status)

        # return effect URL - there might have been a redirect and the response URL is the final one
        return response.status < 299, response.geturl()

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        try:
            success, final_url = self.execute(arguments)
            status_msg = "✅ PUT operation successful" if success else "⚠️ PUT operation completed with warnings"
            return [
                types.TextContent(type="text", text=status_msg),
                types.TextContent(type="text", text=f"Final URL: {final_url}")
            ]
        except HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason} when accessing {e.url}"
            return [
                types.TextContent(type="text", text=error_msg)
            ]

