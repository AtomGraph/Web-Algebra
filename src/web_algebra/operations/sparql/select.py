from typing import Any
import logging
import rdflib
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from rdflib.query import Result
from web_algebra.client import SPARQLClient


class SELECT(Operation):
    """
    Executes SPARQL SELECT queries against endpoints
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = SPARQLClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,
        )

    @classmethod
    def description(cls) -> str:
        return "Executes SPARQL SELECT queries against endpoints"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "SPARQL endpoint URL"},
                "query": {"type": "string", "description": "SPARQL SELECT query"},
            },
            "required": ["endpoint", "query"],
        }

    def execute(self, endpoint: rdflib.URIRef, query: rdflib.Literal) -> Result:
        """Pure function: execute SPARQL query"""
        endpoint_url = str(endpoint)
        query_str = str(query)

        logging.info(
            "Executing SPARQL SELECT on %s with query:\n%s", endpoint_url, query_str
        )

        # Execute using the SPARQL client
        sparql_json = self.client.query(endpoint_url, query_str)
        logging.info(
            "SPARQL SELECT query returned %d bindings.",
            len(sparql_json.get("results", {}).get("bindings", [])),
        )

        # Convert to JSONResult for compatibility
        from web_algebra.json_result import JSONResult

        return JSONResult.from_json(sparql_json)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"SELECT operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        # Process query
        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        if not isinstance(query_data, Literal) or query_data.datatype != XSD.string:
            raise TypeError(
                f"SELECT operation expects 'query' to be string Literal, got {type(query_data)}"
            )

        return self.execute(endpoint_data, query_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        endpoint = URIRef(arguments["endpoint"])
        query = Literal(arguments["query"], datatype=XSD.string)

        result = self.execute(endpoint, query)

        # Return summary for MCP
        return [
            types.TextContent(
                type="text",
                text=f"SPARQL query returned {len(result.bindings)} results",
            )
        ]
