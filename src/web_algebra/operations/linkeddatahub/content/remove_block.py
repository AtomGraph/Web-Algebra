from typing import Any
import logging
from mcp import types
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.patch import PATCH


class RemoveBlock(PATCH):
    @classmethod
    def name(cls):
        return "ldh-RemoveBlock"

    @classmethod
    def description(cls) -> str:
        return """Removes a content block from a LinkedDataHub document.
        
        This tool removes content blocks from LinkedDataHub documents by:
        - Deleting the sequence property that references the block (rdf:_N)
        - Deleting all properties of the block itself
        - If no specific block URI is provided, removes any blocks found via sequence properties
        
        The operation uses SPARQL UPDATE (HTTP PATCH) to perform the deletion."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URI of the document to remove the block from.",
                },
                "block": {
                    "type": "string",
                    "description": "Optional URI of the specific content block to remove. If not provided, will remove blocks based on sequence properties.",
                },
            },
            "required": ["url"],
        }

    def execute_json(self, arguments: dict[str, str], variable_stack: list = []) -> Any:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(f"RemoveBlock operation expects 'url' to be URIRef, got {type(url_data)}")

        # Process optional arguments
        block_uri = None
        if "block" in arguments:
            block_data = Operation.process_json(
                self.settings, arguments["block"], self.context, variable_stack
            )
            if not isinstance(block_data, URIRef):
                raise TypeError(f"RemoveBlock operation expects 'block' to be URIRef, got {type(block_data)}")
            block_uri = block_data
            
        return self.execute(url_data, block_uri)

    def execute(
        self,
        url: URIRef,
        block: URIRef = None,
    ) -> Any:
        """Pure function: remove content block with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(f"RemoveBlock.execute expects url to be URIRef, got {type(url)}")
        if block is not None and not isinstance(block, URIRef):
            raise TypeError(f"RemoveBlock.execute expects block to be URIRef, got {type(block)}")

        url_str = str(url)
        block_str = str(block) if block else None

        logging.info("Removing block from document <%s>", url_str)
        if block_str:
            logging.info("Targeting specific block <%s>", block_str)

        # Construct SPARQL UPDATE query
        # If block is specified, use it as <block_uri>, otherwise use ?block variable
        block_ref = f"<{block_str}>" if block_str else "?block"

        sparql_query = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

DELETE
{{
    <{url_str}> ?seq {block_ref} .
    {block_ref} ?p ?o .
}}
WHERE
{{
    <{url_str}> ?seq {block_ref} .
    FILTER(strstarts(str(?seq), concat(str(rdf:), "_")))
    OPTIONAL
    {{
        {block_ref} ?p ?o
    }}
}}"""

        logging.info(f"SPARQL UPDATE query: {sparql_query}")

        # Use parent PATCH operation to execute the SPARQL UPDATE
        return super().execute(url, Literal(sparql_query, datatype=XSD.string))

    def mcp_run(
        self,
        arguments: dict[str, Any],
        context: Any = None,
    ) -> Any:
        """MCP execution: plain args → plain results"""
        url = URIRef(arguments["url"])
        block = None
        if "block" in arguments and arguments["block"]:
            block = URIRef(arguments["block"])
        
        self.execute(url, block)
        
        block_text = (
            f"Block: {block}"
            if block
            else "Any blocks found via sequence properties"
        )
        
        return [
            types.TextContent(
                type="text",
                text=f"Removed content block from document: {str(url)}\n{block_text}\nResult: Block(s) successfully removed",
            )
        ]
