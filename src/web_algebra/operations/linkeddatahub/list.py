from typing import Any
import logging
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
from web_algebra.operation import Operation
from web_algebra.operations.sparql.substitute import Substitute
from web_algebra.operations.sparql.select import SELECT, sparql_json_to_csv

class LDHList(Operation):

    # same query as ldh:SelectChildren in ldh.ttl
    query: str = """
        PREFIX  dct:  <http://purl.org/dc/terms/>
        PREFIX  foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX  sioc: <http://rdfs.org/sioc/ns#>

        SELECT DISTINCT  ?child ?thing
        WHERE
        { GRAPH ?childGraph
        {   { ?child  sioc:has_parent  $this }
            UNION
            { ?child  sioc:has_container  $this }
            ?child  a                     ?Type
            OPTIONAL
            { ?child  dct:title  ?title }
            OPTIONAL
            { ?child  foaf:primaryTopic  ?thing }
        }
        }
        ORDER BY ?title
    """

    @classmethod
    def name(cls):
        return "ldh-List"
    
    @classmethod
    def description(cls) -> str:
        return "Returns a list of children documents for the given URL."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL of the document to list children for."},
                "endpoint": {"type": "string", "description": "The SPARQL endpoint URL to query."},
                "base": {"type": "string", "description": "Base URL for constructing the SPARQL endpoint. Needs to end with a slash."}
            },
            "required": ["url"],
            "oneOf": [
                {"required": ["endpoint"]},
                {"required": ["base"]}
            ]
        }
    
    def execute(self, arguments: dict[str, str]) -> list[dict]:
        """
        :arguments: A dictionary containing:
            - `url`: The URL of the document to list children for.
            - `endpoint`: The SPARQL endpoint URL to query.
            - `base`: Base URL for constructing the SPARQL endpoint (optional if `endpoint` is provided).
        :return: A list of dictionaries representing the children documents.
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("LDHList operation expects 'url' to be a string.")
        
        if "endpoint" in arguments:
            endpoint: str = Operation.execute_json(self.settings, arguments["endpoint"], self.context)
            if not isinstance(endpoint, str):
                raise ValueError("LDHList operation expects 'endpoint' to be a string.")
        elif "base" in arguments:
            base: str = Operation.execute_json(self.settings, arguments["base"], self.context)
            if not base.endswith("/"):
                base += "/"
            if not isinstance(base, str):
                raise ValueError("LDHList operation expects 'base' to be a string.")
            endpoint = base + "sparql"
        else:
            raise ValueError("LDHList operation requires either 'endpoint' or 'base' to be provided.")
        
        logging.info(f"Executing ldh:List on <%s> (SPARQL endpoint: %s)", url, endpoint)

        substitute = Substitute(settings=self.settings, context=self.context)
        query = substitute.execute({
                "query": self.query,
                "var": "this",
                "binding": {"value": url, "type": "uri"}
            })
        
        select = SELECT(settings=self.settings, context=self.context)
        return select.execute({
            "query": query,
            "endpoint": endpoint,
        })


    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        return [types.TextContent(type="text", text=sparql_json_to_csv(self.execute(arguments)))]