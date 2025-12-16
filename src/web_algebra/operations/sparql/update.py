from typing import Any
import logging
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from rdflib.query import Result
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.client import SPARQLClient


class Update(Operation, MCPTool):
    """
    Executes SPARQL UPDATE operations against endpoints.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = SPARQLClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,
        )

    @classmethod
    def description(cls) -> str:
        return "Executes SPARQL UPDATE operations against endpoints"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "SPARQL update endpoint URL",
                },
                "update": {
                    "type": "string",
                    "description": "SPARQL UPDATE query string",
                },
            },
            "required": ["endpoint", "update"],
        }

    def execute(self, endpoint: URIRef, update: Literal) -> Result:
        """Pure function: execute SPARQL UPDATE"""
        endpoint_url = str(endpoint)
        update_str = str(update)

        logging.info(
            "Executing SPARQL UPDATE on %s with update:\n%s", endpoint_url, update_str
        )

        # Execute using the SPARQL client
        response = self.client.update(endpoint_url, update_str)
        logging.info("SPARQL UPDATE operation status: %s", response.status)

        # Return SPARQL results format with status
        from web_algebra.json_result import JSONResult

        return JSONResult(
            vars=["status", "url"],
            bindings=[
                {
                    "status": Literal(response.status, datatype=XSD.integer),
                    "url": URIRef(response.geturl()),
                }
            ],
        )

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"Update operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        # Process update query
        update_data = Operation.process_json(
            self.settings, arguments["update"], self.context, variable_stack
        )
        if not isinstance(update_data, Literal) or update_data.datatype != XSD.string:
            raise TypeError(
                f"Update operation expects 'update' to be string Literal, got {type(update_data)}"
            )

        return self.execute(endpoint_data, update_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        endpoint = URIRef(arguments["endpoint"])
        update = Literal(arguments["update"], datatype=XSD.string)

        result = self.execute(endpoint, update)

        # Extract status for MCP response
        status_binding = result.bindings[0]["status"]
        return [
            types.TextContent(
                type="text", text=f"SPARQL UPDATE status: {status_binding}"
            )
        ]
