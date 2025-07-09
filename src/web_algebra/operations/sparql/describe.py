import logging
from typing import Any
import json
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.client import SPARQLClient

class DESCRIBE(Operation):
    """
    Executes a SPARQL DESCRIBE query against a specified endpoint and returns a JSON-LD response.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = SPARQLClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Executes a SPARQL DESCRIBE query."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["endpoint", "query"]
        }
   
    def execute(self, arguments: dict[str, Any]) -> dict:
        """
        :arguments: A dictionary containing:
            - `endpoint`: The SPARQL endpoint URL to query.
            - `query`: The SPARQL DESCRIBE query string to execute.
        :return: A Python dict representing the JSON-LD response from the SPARQL DESCRIBE query."""
        endpoint: str = Operation.execute_json(self.settings, arguments["endpoint"], self.context)
        query: str = Operation.execute_json(self.settings, arguments["query"], self.context)

        if not isinstance(query, str):
            raise ValueError("DESCRIBE operation expects 'query' to be a string.")

        logging.info(f"Executing SPARQL DESCRIBE on %s with query:\n%s", endpoint, query)
        return self.client.query(endpoint, query)

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        json_ld_data = self.execute(arguments)
        jsonld_str = json.dumps(json_ld_data)
        
        logging.info("Returning JSON-LD data as text content.")
        return [types.TextContent(type="text", text=jsonld_str)]
