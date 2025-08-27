from typing import Any
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST
from web_algebra.operations.linked_data.get import GET


class AddObjectBlock(POST):
    @classmethod
    def name(cls):
        return "ldh-AddObjectBlock"

    @classmethod
    def description(cls) -> str:
        return """Appends an object block to a LinkedDataHub document content mode using sequence properties.
        Only XHTML blocks and object blocks are shown in the content mode. Other resources can still be added to the document, but they will not be displayed in the content mode.
        
        Object blocks reference external resources via URI and can have different display modes.
        Only RDF Linked Data objects can be rendered by using display modes, so if you think you're using an RDF URI value, make sure it returns a valid RDF resource (e.g. use the GET operation to verify).
        Non-RDF resources (for example images) will be embedded using HTML <object> element.

        Possible display modes include:
        - https://w3id.org/atomgraph/client#ReadMode: Default mode for displaying the object.
        - https://w3id.org/atomgraph/client#GraphMode: Displays the object as a graph.
        - https://w3id.org/atomgraph/client#MapMode: Displays the object as a map.
        - https://w3id.org/atomgraph/client#ChartMode: Displays the object as a chart.
        
        This tool:
        - Fetches the current document to find the next sequence number (rdf:_1, rdf:_2, etc.)
        - Creates an ldh:Object resource with rdf:value pointing to the target resource URI
        - Posts the new object block to the target document
        - Supports optional title, description, fragment identifier, and display mode
        
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
                    "description": "The URI of the document to append the object block to.",
                },
                "value": {
                    "type": "string",
                    "description": "URI of the object resource to reference.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional title for the object block.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for the object block.",
                },
                "fragment": {
                    "type": "string",
                    "description": "Optional fragment identifier for the object block URI (e.g., 'intro' creates #intro).",
                },
                "mode": {
                    "type": "string",
                    "description": "Optional URI of the block mode. Defaults to ReadMode if not specified.",
                    "enum": [
                        "https://w3id.org/atomgraph/client#GraphMode",
                        "https://w3id.org/atomgraph/client#MapMode",
                        "https://w3id.org/atomgraph/client#ChartMode",
                        "https://w3id.org/atomgraph/client#ReadMode",
                    ],
                    "default": "https://w3id.org/atomgraph/client#ReadMode",
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
                f"AddObjectBlock operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        value_data = Operation.process_json(
            self.settings, arguments["value"], self.context, variable_stack
        )
        if not isinstance(value_data, URIRef):
            raise TypeError(
                f"AddObjectBlock operation expects 'value' to be URIRef, got {type(value_data)}"
            )

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

        mode_uri = None
        if "mode" in arguments:
            mode_data = Operation.process_json(
                self.settings, arguments["mode"], self.context, variable_stack
            )
            if not isinstance(mode_data, URIRef):
                raise TypeError(
                    f"AddObjectBlock operation expects 'mode' to be URIRef, got {type(mode_data)}"
                )
            mode_uri = mode_data

        return self.execute(
            url_data,
            value_data,
            title_literal,
            description_literal,
            fragment_literal,
            mode_uri,
        )

    def execute(
        self,
        url: URIRef,
        value: URIRef,
        title: Literal = None,
        description: Literal = None,
        fragment: Literal = None,
        mode: URIRef = None,
    ) -> Any:
        """Pure function: create object block with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"AddObjectBlock.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(value, URIRef):
            raise TypeError(
                f"AddObjectBlock.execute expects value to be URIRef, got {type(value)}"
            )
        if title is not None and (
            not isinstance(title, Literal) or title.datatype != XSD.string
        ):
            raise TypeError(
                f"AddObjectBlock.execute expects title to be string Literal, got {type(title)}"
            )
        if description is not None and (
            not isinstance(description, Literal) or description.datatype != XSD.string
        ):
            raise TypeError(
                f"AddObjectBlock.execute expects description to be string Literal, got {type(description)}"
            )
        if fragment is not None and (
            not isinstance(fragment, Literal) or fragment.datatype != XSD.string
        ):
            raise TypeError(
                f"AddObjectBlock.execute expects fragment to be string Literal, got {type(fragment)}"
            )
        if mode is not None and not isinstance(mode, URIRef):
            raise TypeError(
                f"AddObjectBlock.execute expects mode to be URIRef, got {type(mode)}"
            )

        url_str = str(url)
        value_str = str(value)
        title_str = str(title) if title else None
        description_str = str(description) if description else None
        fragment_str = str(fragment) if fragment else None
        mode_str = str(mode) if mode else None

        logging.info(
            "Creating object block for document <%s> with value <%s>",
            url_str,
            value_str,
        )

        # Step 1: Get current document to find next sequence number
        get_op = GET(settings=self.settings, context=self.context)
        graph = get_op.execute(url)

        # Convert Graph to JSON-LD for processing
        import json

        jsonld_str = graph.serialize(format="json-ld")
        doc = json.loads(jsonld_str)

        # Step 2: Extract sequence numbers from rdf:_N properties in JSON-LD list
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
            block_id = "_:object-block"

        # Step 5: Build JSON-LD structure for the object block
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "ac": "https://w3id.org/atomgraph/client#",
            },
            "@id": url_str,
        }

        # Add the object block resource
        block = {
            "@id": block_id,
            "@type": "ldh:Object",
            "rdf:value": {"@id": value_str},
        }

        # Add optional properties to object block
        if title_str:
            block["dct:title"] = title_str

        if description_str:
            block["dct:description"] = description_str

        if mode_str:
            block["ac:mode"] = {"@id": mode_str}

        # Add object block to the data structure
        data[sequence_property] = block

        logging.info(f"Posting object block with JSON-LD data: {data}")

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
        value = URIRef(arguments["value"])

        title = None
        if "title" in arguments:
            title = Literal(arguments["title"], datatype=XSD.string)

        description = None
        if "description" in arguments:
            description = Literal(arguments["description"], datatype=XSD.string)

        fragment = None
        if "fragment" in arguments:
            fragment = Literal(arguments["fragment"], datatype=XSD.string)

        mode = None
        if "mode" in arguments:
            mode = URIRef(arguments["mode"])

        # Call pure function
        result = self.execute(url, value, title, description, fragment, mode)

        # Return status for MCP response
        status_binding = result.bindings[0]["status"]
        return [types.TextContent(type="text", text=f"Object block added - status: {status_binding}")]
