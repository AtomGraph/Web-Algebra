import logging
from typing import Any
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.client import SPARQLClient

class CONSTRUCT(Operation):
    """
    Executes a SPARQL CONSTRUCT query against a specified endpoint and returns a Python dict with the JSON-LD response.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = SPARQLClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    @property
    def description(self) -> str:
        return "Executes a SPARQL CONSTRUCT query against a specified endpoint and returns the RDF data as a Python dict of JSON-LD."
    
    @property
    def inputSchema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "The SPARQL endpoint URL to query."
                },
                "query": {
                    "type": "string",
                    "description": "The SPARQL CONSTRUCT query string to execute."
                }
            },
            "required": ["endpoint", "query"]
        }
   
    def execute(self, arguments: dict[str, Any]) -> dict:
        """
        :arguments: A dictionary containing:
            - `endpoint`: The SPARQL endpoint URL to query.
            - `query`: The SPARQL CONSTRUCT query string to execute.
        :return: A Python dict representing the JSON-LD response from the SPARQL CONSTRUCT query."""
        endpoint: str = Operation.execute_json(self.settings, arguments["endpoint"], self.context)
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)

        if not isinstance(query, str):
            raise ValueError("CONSTRUCT operation expects 'query' to be a string.")

        logging.info(f"Executing SPARQL CONSTRUCT on %s with query:\n%s", endpoint, query)
        return self.client.query(endpoint, query)

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=str(self.execute(arguments)))]
