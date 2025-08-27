from typing import Any
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD, RDF
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST
from web_algebra.operations.linked_data.get import GET


class AddXHTMLBlock(POST):
    @classmethod
    def name(cls):
        return "ldh-AddXHTMLBlock"

    @classmethod
    def description(cls) -> str:
        return """Appends an XHTML block to a LinkedDataHub document using sequence properties.
        Only XHTML blocks and object blocks are shown in the content mode. Other resources can still be added to the document, but they will not be displayed in the content mode.

        IMPORTANT: The value parameter must be canonical XML literal - well-formed XHTML content
        that will be stored as rdf:XMLLiteral datatype.
        The top-level XHTML element must be <div xmlns="http://www.w3.org/1999/xhtml"></div>.
        The XHTML can use CSS classes for inline elements from Bootstrap 2.3.2, but no inline CSS styles.
        
        Canonical XML Rules (TL;DR):
        ✅ Well-formed XML - proper opening/closing tags, escaped special chars (&lt; &gt; &amp;)
        ✅ Attributes alphabetically ordered - <tag attr1="x" attr2="y"> not <tag attr2="y" attr1="x">
        ✅ No comments or processing instructions - strip <!-- --> and <?xml ?>
        ✅ Consistent encoding - UTF-8, normalized whitespace
        Bottom line: Valid XML + deterministic formatting = canonical XML.
        
        This tool:
        - Fetches the current document to find the next sequence number (rdf:_1, rdf:_2, etc.)
        - Creates an ldh:XHTML resource with rdf:value containing the XML literal
        - Posts the new XHTML block to the target document
        - Supports optional title, description, and fragment identifier
        
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
                    "description": "The URI of the document to append the XHTML block to.",
                },
                "value": {
                    "type": "string",
                    "description": "XHTML content as canonical XML literal (must be well-formed XML).",
                },
                "title": {
                    "type": "string",
                    "description": "Optional title for the XHTML block.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for the XHTML block.",
                },
                "fragment": {
                    "type": "string",
                    "description": "Optional fragment identifier for the XHTML block URI (e.g., 'intro' creates #intro).",
                },
            },
            "required": ["url", "value"],
        }

    def execute_json(self, arguments: dict[str, str], variable_stack: list = []) -> Any:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"AddXHTMLBlock operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        value_data = Operation.process_json(
            self.settings, arguments["value"], self.context, variable_stack
        )
        # For XHTML, we need to create an XML literal with specific datatype
        if isinstance(value_data, str):
            value_literal = Literal(value_data, datatype=RDF.XMLLiteral)
        elif isinstance(value_data, Literal):
            # Ensure it's an XML literal
            value_literal = Literal(str(value_data), datatype=RDF.XMLLiteral)
        else:
            value_str = self.to_string_literal(value_data)
            value_literal = Literal(str(value_str), datatype=RDF.XMLLiteral)

        # Process optional arguments
        title_literal = None
        if "title" in arguments:
            title_data = Operation.process_json(
                self.settings, arguments["title"], self.context, variable_stack
            )
            title_literal = self.to_string_literal(title_data)

        description_literal = None
        if "description" in arguments:
            description_data = Operation.process_json(
                self.settings, arguments["description"], self.context, variable_stack
            )
            description_literal = self.to_string_literal(description_data)

        fragment_literal = None
        if "fragment" in arguments:
            fragment_data = Operation.process_json(
                self.settings, arguments["fragment"], self.context, variable_stack
            )
            fragment_literal = self.to_string_literal(fragment_data)

        return self.execute(
            url_data,
            value_literal,
            title_literal,
            description_literal,
            fragment_literal,
        )

    def execute(
        self,
        url: URIRef,
        value: Literal,
        title: Literal = None,
        description: Literal = None,
        fragment: Literal = None,
    ) -> Any:
        """Pure function: create XHTML block with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"AddXHTMLBlock.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(value, Literal) or value.datatype != RDF.XMLLiteral:
            raise TypeError(
                f"AddXHTMLBlock.execute expects value to be XMLLiteral, got {type(value)}"
            )
        if title is not None and (
            not isinstance(title, Literal) or title.datatype != XSD.string
        ):
            raise TypeError(
                f"AddXHTMLBlock.execute expects title to be string Literal, got {type(title)}"
            )
        if description is not None and (
            not isinstance(description, Literal) or description.datatype != XSD.string
        ):
            raise TypeError(
                f"AddXHTMLBlock.execute expects description to be string Literal, got {type(description)}"
            )
        if fragment is not None and (
            not isinstance(fragment, Literal) or fragment.datatype != XSD.string
        ):
            raise TypeError(
                f"AddXHTMLBlock.execute expects fragment to be string Literal, got {type(fragment)}"
            )

        url_str = str(url)
        value_str = str(value)
        title_str = str(title) if title else None
        description_str = str(description) if description else None
        fragment_str = str(fragment) if fragment else None

        logging.info("Creating XHTML block for document <%s>", url_str)

        # Step 1: Get current document to find next sequence number
        get_op = GET(settings=self.settings, context=self.context)
        graph = get_op.execute(url)

        # Convert Graph to JSON-LD for processing
        import json

        jsonld_str = graph.serialize(format="json-ld")
        doc = json.loads(jsonld_str)

        # Step 2: Extract sequence numbers from rdf:_N properties in JSON-LD @graph
        sequence_numbers = []
        if isinstance(doc, list):
            for resource in doc:
                if resource.get("@id") == url_str:
                    # Look for rdf:_N properties
                    for key in resource.keys():
                        if key.startswith(
                            "http://www.w3.org/1999/02/22-rdf-syntax-ns#_"
                        ):
                            # Extract the sequence number from the property URI
                            seq_num = key.split("#_")[-1]
                            try:
                                sequence_numbers.append(int(seq_num))
                            except ValueError:
                                continue
                    break
        else:
            raise ValueError(
                "Expected a list of resources from GET operation, got: %s", type(doc)
            )

        # Step 3: Determine next sequence number
        next_sequence = max(sequence_numbers, default=0) + 1
        sequence_property = (
            f"http://www.w3.org/1999/02/22-rdf-syntax-ns#_{next_sequence}"
        )

        logging.info(f"Next sequence number: {next_sequence}")

        # Step 4: Create subject URI (fragment or blank node)
        if fragment_str:
            block_id = f"{url_str}#{fragment_str}"
        else:
            block_id = "_:xhtml-block"

        # Step 5: Build JSON-LD structure for the XHTML block
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            },
            "@id": url_str,
        }

        # Add the XHTML block resource
        block = {
            "@id": block_id,
            "@type": "ldh:XHTML",
            "rdf:value": {"@type": "rdf:XMLLiteral", "@value": value_str},
        }

        # Add optional properties to XHTML block
        if title_str:
            block["dct:title"] = title_str

        if description_str:
            block["dct:description"] = description_str

        # Add XHTML block to the data structure
        data[sequence_property] = block

        logging.info(f"Posting XHTML block with JSON-LD data: {data}")

        # Step 6: POST the JSON-LD content to the target URI
        # Convert JSON-LD dict to Graph
        from rdflib import Graph

        graph = Graph()
        graph.parse(data=json.dumps(data), format="json-ld", base=url_str)
        return super().execute(url, graph)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        from mcp import types

        # Convert plain arguments to RDFLib terms
        url = URIRef(arguments["url"])
        value = Literal(arguments["value"], datatype=RDF.XMLLiteral)

        title = None
        if "title" in arguments:
            title = Literal(arguments["title"], datatype=XSD.string)

        description = None
        if "description" in arguments:
            description = Literal(arguments["description"], datatype=XSD.string)

        fragment = None
        if "fragment" in arguments:
            fragment = Literal(arguments["fragment"], datatype=XSD.string)

        # Call pure function
        result = self.execute(url, value, title, description, fragment)

        # Return status for MCP response
        status_binding = result.bindings[0]["status"]
        return [types.TextContent(type="text", text=f"XHTML block added - status: {status_binding}")]
