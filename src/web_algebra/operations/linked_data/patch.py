from typing import Any
import logging
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from rdflib.query import Result
from web_algebra.client import LinkedDataClient


class PATCH(Operation):
    """
    Updates RDF data in a named graph using HTTP PATCH with SPARQL Update.
    The URL serves as both the resource identifier and the named graph address in systems with direct graph identification.
    Updates the RDF graph at that URL using the SPARQL update payload provided in the `update` argument.
    Returns True if the operation was successful, False otherwise.
    Note: This operation does not return the updated graph, it only confirms the success of the operation.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return """
        Updates RDF data in a named graph using HTTP PATCH with SPARQL Update.
        The URL serves as both the resource identifier and the named graph address in systems with direct graph identification.
        Updates the RDF graph at that URL using the SPARQL update payload provided in the `update` argument.
        Returns True if the operation was successful, False otherwise.
        Note: This operation does not return the updated graph, it only confirms the success of the operation.
        """

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to send the SPARQL UPDATE to. This should be a valid URL.",
                },
                "update": {
                    "type": "string",
                    "description": "The SPARQL update string to execute.",
                },
            },
            "required": ["url", "update"],
        }

    def execute(self, url: URIRef, update: Literal) -> Result:
        """Pure function: PATCH SPARQL update to URL with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(f"PATCH.execute expects url to be URIRef, got {type(url)}")
        if not isinstance(update, Literal):
            raise TypeError(
                f"PATCH.execute expects update to be Literal, got {type(update)}"
            )

        url_str = str(url)
        update_str = str(update)
        logging.info(
            "Executing PATCH operation with URL: %s and SPARQL update: %s",
            url_str,
            update_str,
        )

        response = self.client.patch(url_str, update_str)
        logging.info("PATCH operation status: %s", response.status)

        # Return SPARQL results format
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
        """JSON execution: process arguments and call pure function"""
        # Process URL
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        url = self.json_to_rdflib(url_data)
        if not isinstance(url, URIRef):
            raise TypeError(
                f"PATCH operation expects 'url' to be URIRef, got {type(url)}"
            )

        # Process update query
        update_data = Operation.process_json(
            self.settings, arguments["update"], self.context, variable_stack
        )
        update = self.json_to_rdflib(update_data)
        if not isinstance(update, Literal):
            raise TypeError(
                f"PATCH operation expects 'update' to be Literal, got {type(update)}"
            )

        return self.execute(url, update)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        url = URIRef(arguments["url"])
        update = Literal(arguments["update"], datatype=XSD.string)

        result = self.execute(url, update)

        # Extract status for MCP response
        status_binding = result.bindings[0]["status"]
        return [types.TextContent(type="text", text=f"PATCH status: {status_binding}")]
