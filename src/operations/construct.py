import json
import logging
from typing import Any
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from operation import Operation
from client import SPARQLClient

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
    
    def execute(self, arguments: dict[str, Any]) -> dict:
        """
        :arguments: A dictionary containing:
            - `endpoint`: The SPARQL endpoint URL to query.
            - `query`: The SPARQL CONSTRUCT query string to execute.
        :return: A Python dict representing the JSON-LD response from the SPARQL CONSTRUCT query."""
        endpoint: str = arguments.get("endpoint")
        query: str = arguments["query"]

        if not isinstance(query, str):
            raise ValueError("CONSTRUCT operation expects 'query' to be a string.")

        logging.info(f"Executing SPARQL CONSTRUCT on %s with query:\n%s", endpoint, query)

        # Perform the SPARQL query
        graph = self.client.query(endpoint, query)

        logging.info(f"SPARQL CONSTRUCT query returned {len(graph)} triples.")

        # Serialize the graph as JSON-LD dict
        jsonld_str = graph.serialize(format="json-ld")
        jsonld_data = json.loads(jsonld_str)

        logging.info("Returning the constructed graph as a JSON-LD dict.")
        return jsonld_data

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=str(self.process(arguments)))]
