from typing import Any
import logging
import json
from mcp import types
from rdflib.query import Result
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.operations.sparql.substitute import Substitute
from web_algebra.operations.sparql.select import SELECT


class LDHList(Operation, MCPTool):
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
        return "Returns a list of children documents for the given URL as SPARQL results JSON."

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the document to list children for.",
                },
                "endpoint": {
                    "type": "string",
                    "description": "The SPARQL endpoint URL to query. Either 'endpoint' or 'base' must be provided.",
                },
                "base": {
                    "type": "string",
                    "description": "Base URL for constructing the SPARQL endpoint. Needs to end with a slash. Either 'endpoint' or 'base' must be provided.",
                },
            },
            "required": ["url"],
        }

    def execute(
        self,
        url: URIRef,
        endpoint: URIRef,
    ) -> Result:
        """Pure function: list LinkedDataHub children with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"LDHList.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(endpoint, URIRef):
            raise TypeError(
                f"LDHList.execute expects endpoint to be URIRef, got {type(endpoint)}"
            )

        url_str = str(url)
        endpoint_str = str(endpoint)

        logging.info(
            "Executing ldh:List on <%s> (SPARQL endpoint: %s)", url_str, endpoint_str
        )

        substitute = Substitute(settings=self.settings, context=self.context)
        # Direct call with RDFLib terms
        query_literal = Literal(self.query, datatype=XSD.string)
        var_literal = Literal("this", datatype=XSD.string)
        binding_uriref = url  # Already a URIRef
        query = substitute.execute(query_literal, var_literal, binding_uriref)

        select = SELECT(settings=self.settings, context=self.context)
        # Direct call with RDFLib terms
        # a Result, one row per child (formal-semantics.md Appendix A), so the
        # listing composes with ForEach, Filter and Bindings like any SELECT
        return select.execute(endpoint, query)

    def execute_json(
        self, arguments: dict[str, str], variable_stack: list = None
    ) -> Result:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"LDHList operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        # Process endpoint or base argument
        endpoint_uri = None
        if "endpoint" in arguments:
            endpoint_data = Operation.process_json(
                self.settings, arguments["endpoint"], self.context, variable_stack
            )
            if not isinstance(endpoint_data, URIRef):
                raise TypeError(
                    f"LDHList operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
                )
            endpoint_uri = endpoint_data
        elif "base" in arguments:
            base_data = Operation.process_json(
                self.settings, arguments["base"], self.context, variable_stack
            )
            base_literal = self.to_string_literal(base_data)
            base_str = str(base_literal)
            if not base_str.endswith("/"):
                base_str += "/"
            endpoint_uri = URIRef(base_str + "sparql")
        else:
            raise ValueError(
                "LDHList operation requires either 'endpoint' or 'base' to be provided."
            )

        return self.execute(url_data, endpoint_uri)

    def mcp_run(
        self,
        arguments: dict[str, Any],
        context: Any = None,
    ) -> Any:
        """MCP execution: plain args → plain results"""
        # Convert plain arguments to RDFLib terms
        url = URIRef(arguments["url"])
        if "endpoint" in arguments:
            endpoint = URIRef(arguments["endpoint"])
        elif "base" in arguments:
            base = arguments["base"] if arguments["base"].endswith("/") else arguments["base"] + "/"
            endpoint = URIRef(base + "sparql")
        else:
            raise ValueError("ldh-List requires either 'endpoint' or 'base'")

        # Call pure function; the Result goes out as SPARQL Results JSON
        json_str = json.dumps(self.execute(url, endpoint).to_json())

        logging.info("Returning SPARQL Results JSON data as text content.")
        return [types.TextContent(type="text", text=json_str)]
