import json
import logging
from rdflib import Graph, URIRef
from typing import Any
from mcp import types
from web_algebra.operation import Operation
from web_algebra.client import LinkedDataClient


class GET(Operation):
    """
    Retrieves RDF data from a named graph using HTTP GET.
    The URL serves as both the resource identifier and the named graph address in systems with direct graph identification.
    Returns the RDF graph (describing the resource at that URL) as JSON-LD.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,  # Optionally disable SSL verification
        )

    @classmethod
    def description(cls) -> str:
        return "Retrieves RDF data from a named graph using HTTP GET. The URL serves as both the resource identifier and the named graph address in systems with direct graph identification. Returns the RDF graph describing the resource at that URL."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch RDF data from. This should be a valid URL pointing to RDF content.",
                }
            },
            "required": ["url"],
        }

    def execute(self, url: URIRef) -> Graph:
        """Pure function: GET RDF graph from URL with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(f"GET.execute expects url to be URIRef, got {type(url)}")

        url_str = str(url)
        logging.info("Executing GET operation with URL: %s", url_str)

        graph = self.client.get(url_str)
        logging.info(
            "Successfully fetched RDF data from %s (%s triple(s))", url_str, len(graph)
        )

        return graph

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Graph:
        """JSON execution: process arguments and delegate to execute()"""
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"GET operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        # Return Graph directly (same as execute) - serialization only at boundaries
        return self.execute(url_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> list[types.TextContent]:
        """MCP execution: plain args → plain results"""
        url = URIRef(arguments["url"])

        graph = self.execute(url)

        # Convert Graph to JSON-LD for MCP response
        jsonld_str = graph.serialize(format="json-ld")
        return [types.TextContent(type="text", text=jsonld_str)]
