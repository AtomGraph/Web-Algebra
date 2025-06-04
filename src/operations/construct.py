import json
import logging
from typing import Any
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from operation import Operation
from client import SPARQLClient

class CONSTRUCT(Operation):
    """
    Executes a SPARQL CONSTRUCT query against a specified endpoint and returns a Python dict of JSON-LD.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = SPARQLClient(
            cert_pem_path=getattr(self.settings, 'cert_pem_path', None),
            cert_password=getattr(self.settings, 'cert_password', None),
            verify_ssl=False  # Optionally disable SSL verification
        )

    def execute(self, arguments: dict[str, Any]) -> dict:
        """
        Executes a SPARQL CONSTRUCT query and returns the RDF data as a Python dict of JSON-LD.
        :return: A Python dict containing the JSON-LD representation of the constructed RDF graph.
        """
        endpoint = arguments.get("endpoint")
        query = arguments["query"]

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
