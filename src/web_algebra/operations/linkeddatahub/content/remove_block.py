from typing import Any
import logging
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSessionT
from mcp.shared.context import LifespanContextT
from mcp import types
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
                    "description": "The URI of the document to remove the block from."
                },
                "block": {
                    "type": "string", 
                    "description": "Optional URI of the specific content block to remove. If not provided, will remove blocks based on sequence properties."
                }
            },
            "required": ["url"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Removes a content block from a LinkedDataHub document using SPARQL UPDATE
        
        :arguments: A dictionary containing:
            - `url`: URI of the document to remove block from
            - `block`: Optional URI of the specific block to remove
        :return: Result from PATCH operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("ldh-RemoveBlock operation expects 'url' to be a string.")
        
        block = arguments.get("block")
        if block:
            block = Operation.execute_json(self.settings, block, self.context)
            if not isinstance(block, str):
                raise ValueError("ldh-RemoveBlock operation expects 'block' to be a string.")
        
        logging.info(f"Removing block from document <%s>", url)
        if block:
            logging.info(f"Targeting specific block <%s>", block)
        
        # Construct SPARQL UPDATE query
        # If block is specified, use it as <block_uri>, otherwise use ?block variable
        block_ref = f"<{block}>" if block else "?block"
        
        sparql_query = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

DELETE
{{
    <{url}> ?seq {block_ref} .
    {block_ref} ?p ?o .
}}
WHERE
{{
    <{url}> ?seq {block_ref} .
    FILTER(strstarts(str(?seq), concat(str(rdf:), "_")))
    OPTIONAL
    {{
        {block_ref} ?p ?o
    }}
}}"""

        logging.info(f"SPARQL UPDATE query: {sparql_query}")
        
        # Use parent PATCH operation to execute the SPARQL UPDATE
        return super().execute({
            "url": url,
            "query": sparql_query
        })

    def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT] | None = None,
    ) -> Any:
        try:
            result = self.execute(arguments)
            url = Operation.execute_json(self.settings, arguments["url"], self.context)
            block = arguments.get("block")
            block_text = f"Block: {block}" if block else "Any blocks found via sequence properties"
            
            return [types.TextContent(
                type="text", 
                text=f"Removed content block from document: {url}\n{block_text}\nResult: Block(s) successfully removed"
            )]
        except Exception as e:
            return [types.TextContent(
                type="text", 
                text=f"Error removing block: {str(e)}"
            )]
