from typing import Any
import json
import logging
import rdflib
from rdflib import URIRef, Graph, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from rdflib.query import Result
from web_algebra.client import LinkedDataClient


class POST(Operation, MCPTool):
    """
    Creates or appends RDF data to a named graph using HTTP POST.
    The URL serves as both the resource identifier and the named graph address in systems with direct graph identification.
    Creates or adds to the RDF graph (provided as JSON-LD payload) at that URL.
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
        return """Creates or appends RDF data to a named graph using HTTP POST.
        The URL serves as both the resource identifier and the named graph address in systems with direct graph identification.
        Creates or adds to the RDF graph (provided as JSON-LD payload) at that URL.
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
                    "description": "The URL to send the RDF data to. This should be a valid URL.",
                },
                "data": {
                    "type": "object",
                    "description": "The RDF data to append, represented as a JSON-LD dict.",
                },
            },
            "required": ["url", "data"],
        }

    def execute(self, url: rdflib.URIRef, data: rdflib.Graph) -> Result:
        """Pure function: POST RDF graph to URL with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(f"POST operation expects url to be URIRef, got {type(url)}")
        if not isinstance(data, Graph):
            raise TypeError(
                f"POST operation expects data to be Graph, got {type(data)}"
            )

        url_str = str(url)
        logging.info("Executing POST operation with URL: %s", url_str)

        response = self.client.post(url_str, data)
        logging.info("POST operation status: %s", response.status)

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
        """JSON execution: process arguments with strict type checking"""
        # Process URL
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"POST operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        # Process data - may return dict with processed nested operations
        data_result = Operation.process_json(
            self.settings, arguments["data"], self.context, variable_stack
        )

        # Convert processed data to Graph object
        if isinstance(data_result, Graph):
            # Already a Graph (from some operation result)
            graph_data = data_result
        elif isinstance(data_result, dict):
            # Processed JSON-LD - convert to Graph
            import json

            json_str = json.dumps(data_result)
            graph = Graph()
            graph.parse(data=json_str, format="json-ld", base=str(url_data))
            graph_data = graph
        else:
            raise TypeError(
                f"POST operation expects data to be Graph or dict, got {type(data_result)}"
            )

        return self.execute(url_data, graph_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        url = URIRef(arguments["url"])

        # Convert JSON-LD data to Graph
        data_dict = arguments["data"]
        json_str = json.dumps(data_dict)
        graph = Graph()
        graph.parse(data=json_str, format="json-ld", base=str(url))

        result = self.execute(url, graph)

        # Extract status for MCP response
        status_binding = result.bindings[0]["status"]
        return [types.TextContent(type="text", text=f"POST status: {status_binding}")]
