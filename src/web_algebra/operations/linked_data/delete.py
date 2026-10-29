from typing import ClassVar, Any
import logging
from rdflib import URIRef
from mcp import types
from web_algebra.mcp_tool import MCPTool
from web_algebra.client_operation import ClientOperation
from web_algebra.operation import Operation, OperationKind
from rdflib.query import Result


class DELETE(ClientOperation, Operation, MCPTool):
    """
    Removes the named graph at a URL using HTTP DELETE.
    The URL serves as both the resource identifier and the named graph address in systems with direct graph identification.
    Returns the one-row status/url result; a resource that does not exist is answered 404, which is an error.
    """

    # removes the whole document, and the client sends the If-Match that lets it through
    kind: ClassVar[OperationKind] = OperationKind.DESTRUCTIVE


    @classmethod
    def description(cls) -> str:
        return """Removes the named graph at a URL using HTTP DELETE.
        The URL serves as both the resource identifier and the named graph address in systems with direct graph identification.
        The document and all of its RDF data are removed.
        Returns the HTTP status and the URL removed. A URL that does not exist is answered 404, which is an error.
        """

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the document to delete. This should be a valid URL.",
                },
            },
            "required": ["url"],
        }

    def execute(self, url: URIRef) -> Result:
        """Pure function: DELETE the resource at URL with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(f"DELETE operation expects url to be URIRef, got {type(url)}")

        url_str = str(url)
        logging.info("Executing DELETE operation with URL: %s", url_str)

        response = self.client.delete(url_str)
        logging.info("DELETE operation status: %s", response.status)

        return self.written_response(response)

    def execute_json(self, arguments: dict, variable_stack: list = None) -> Result:
        """JSON execution: process arguments with strict type checking"""
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"DELETE operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        return self.execute(url_data)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        url = URIRef(arguments["url"])

        result = self.execute(url)

        # Extract status for MCP response
        status_binding = result.bindings[0]["status"]
        return [types.TextContent(type="text", text=f"DELETE status: {status_binding}")]
