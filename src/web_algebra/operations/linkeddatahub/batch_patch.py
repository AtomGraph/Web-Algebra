from typing import Any
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from mcp import types
from web_algebra.operation import Operation
from web_algebra.operations.sparql.update import Update
from rdflib.query import Result


class BatchPATCH(Update):
    """
    Executes batched SPARQL update operations on LinkedDataHub's /update endpoint.

    IMPORTANT CONSTRAINTS:
    - Each update operation MUST start with a WITH <graph-uri> clause
    - The WITH clause specifies the target graph (equivalent to the document URI you would PATCH)
    - Only INSERT/DELETE/WHERE or DELETE WHERE operations are supported
    - NO GRAPH patterns are allowed in UPDATE operations
    - All graph URIs must be owned by the authenticated agent
    - Requires owner-level access to the application's /update endpoint
    - Per-graph authorization: Checks ACL.Write access for EACH graph URI
    - Fail-fast behavior: If ANY graph lacks authorization, the ENTIRE batch is rejected (nothing is executed)
    - All graph URIs must be under the same application base URL

    Returns HTTP status code (204 No Content on success, 403 Forbidden on authorization failure,
    422 Unprocessable Entity on validation errors, 400 Bad Request on malformed update).
    """

    @classmethod
    def name(cls):
        return "ldh-BatchPATCH"

    @classmethod
    def description(cls) -> str:
        return """Executes batched SPARQL UPDATE operations on LinkedDataHub's /update endpoint.

        IMPORTANT CONSTRAINTS:
        - Each UPDATE operation MUST include a WITH <graph-uri> clause
        - The WITH clause specifies the target graph (equivalent to the document URI you would PATCH)
        - Only INSERT/DELETE/WHERE or DELETE WHERE operations are supported
        - NO GRAPH patterns are allowed in UPDATE operations
        - All graph URIs must be owned by the authenticated agent
        - Requires owner-level access to the application's /update endpoint
        - Per-graph authorization: Checks ACL.Write access for EACH graph URI
        - Fail-fast behavior: If ANY graph lacks authorization, the ENTIRE batch is rejected (nothing is executed)
        - All graph URIs must be under the same application base URL"""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "The LinkedDataHub /update endpoint URL (e.g., 'https://localhost:4443/update')",
                },
                "update": {
                    "type": "string",
                    "description": "The batched SPARQL UPDATE query string with WITH <graph-uri> clauses",
                },
            },
            "required": ["endpoint", "update"],
        }

    def execute(self, endpoint: URIRef, update: Literal) -> Result:
        """Pure function: Execute batched SPARQL UPDATE on LinkedDataHub"""
        if not isinstance(endpoint, URIRef):
            raise TypeError(
                f"ldh-BatchPATCH.execute expects endpoint to be URIRef, got {type(endpoint)}"
            )
        if not isinstance(update, Literal):
            raise TypeError(
                f"ldh-BatchPATCH.execute expects update to be Literal, got {type(update)}"
            )

        # Call parent Update operation
        return super().execute(endpoint, update)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint URL
        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        endpoint = Operation.json_to_rdflib(endpoint_data)
        if not isinstance(endpoint, URIRef):
            raise TypeError(
                f"ldh-BatchPATCH operation expects 'endpoint' to be URIRef, got {type(endpoint)}"
            )

        # Process update query
        update_data = Operation.process_json(
            self.settings, arguments["update"], self.context, variable_stack
        )
        update = Operation.json_to_rdflib(update_data)
        if not isinstance(update, Literal):
            raise TypeError(
                f"ldh-BatchPATCH operation expects 'update' to be Literal, got {type(update)}"
            )

        return self.execute(endpoint, update)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        endpoint = URIRef(arguments["endpoint"])
        update = Literal(arguments["update"], datatype=XSD.string)

        result = self.execute(endpoint, update)

        # Extract status for MCP response
        status_binding = result.bindings[0]["status"]
        return [
            types.TextContent(
                type="text", text=f"ldh-BatchPATCH status: {status_binding}"
            )
        ]
