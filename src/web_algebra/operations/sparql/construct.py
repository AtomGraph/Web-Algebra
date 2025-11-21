import logging
from typing import Any
import json
from rdflib import URIRef, Literal, Graph
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.client import SPARQLClient


class CONSTRUCT(Operation, MCPTool):
    """
    Executes a SPARQL CONSTRUCT query against a specified endpoint.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = SPARQLClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Executes a SPARQL CONSTRUCT query."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["endpoint", "query"],
        }

    def execute(self, endpoint: URIRef, query: Literal) -> Graph:
        """Pure function: execute SPARQL CONSTRUCT query"""
        if not isinstance(endpoint, URIRef):
            raise TypeError(
                f"CONSTRUCT operation expects endpoint to be URIRef, got {type(endpoint)}"
            )
        if not isinstance(query, Literal) or query.datatype != XSD.string:
            raise TypeError(
                f"CONSTRUCT operation expects query to be string Literal, got {type(query)}"
            )

        endpoint_url = str(endpoint)
        query_str = str(query)

        logging.info(
            "Executing SPARQL CONSTRUCT on %s with query:\n%s", endpoint_url, query_str
        )

        # Execute using the SPARQL client and get JSON-LD response
        json_ld_response = self.client.query(endpoint_url, query_str)

        # Convert JSON-LD to RDF Graph
        graph = Graph()
        json_str = json.dumps(json_ld_response)
        graph.parse(data=json_str, format="json-ld")

        return graph

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Graph:
        """JSON execution: process arguments and return Graph (same as execute)"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"CONSTRUCT operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        # Process query
        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        if not isinstance(query_data, Literal) or query_data.datatype != XSD.string:
            raise TypeError(
                f"CONSTRUCT operation expects 'query' to be string Literal, got {type(query_data)}"
            )

        # Return Graph directly (same as execute) - serialization only at boundaries
        return self.execute(endpoint_data, query_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        endpoint = URIRef(arguments["endpoint"])
        query = Literal(arguments["query"], datatype=XSD.string)

        result_graph = self.execute(endpoint, query)

        # Convert Graph back to JSON-LD for MCP response
        json_ld_data = result_graph.serialize(format="json-ld")

        return [types.TextContent(type="text", text=json_ld_data)]
