from typing import Any
import logging
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.client import LinkedDataClient

class PATCH(Operation):
    """
    Updates RDF data in a named graph using HTTP PATCH with SPARQL UPDATE. The URL serves as both the resource identifier and the named graph address in systems with direct graph identification. Updates the RDF graph at that URL.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Updates RDF data in a named graph using HTTP PATCH with SPARQL UPDATE. The URL serves as both the resource identifier and the named graph address in systems with direct graph identification. Updates the RDF graph at that URL."
    
    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to send the SPARQL UPDATE to. This should be a valid URL."
                },
                "query": {
                    "type": "string",
                    "description": "The SPARQL UPDATE query string to execute."
                }
            },
            "required": ["url", "query"]
        }
    
    def execute(self, arguments: dict[str, Any]) -> bool:
        """
        Updates RDF data at the specified URL using the HTTP PATCH method with SPARQL UPDATE.
        :param arguments: A dictionary containing:
            - `url`: The URL to send the SPARQL UPDATE to.
            - `query`: The SPARQL UPDATE query string to execute.
        :return: True if successful, otherwise raises an error.
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)
        logging.info(f"Executing PATCH operation with URL: %s and SPARQL UPDATE: %s", url, query)

        response = self.client.patch(url, query)  # ✅ Send SPARQL UPDATE query
        logging.info("PATCH operation status: %s", response.status)

        return response.status < 299

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=str(self.execute(arguments)))]
