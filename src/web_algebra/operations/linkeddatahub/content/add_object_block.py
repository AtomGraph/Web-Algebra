from typing import Any
import logging
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST
from web_algebra.operations.linked_data.get import GET

class AddObjectBlock(POST):
    
    @classmethod
    def name(cls):
        return "ldh-AddObjectBlock"
    
    @classmethod
    def description(cls) -> str:
        return """Appends an object block to a LinkedDataHub document using sequence properties.
        
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
                    "description": "The URI of the document to append the object block to."
                },
                "value": {
                    "type": "string", 
                    "description": "URI of the object resource to reference."
                },
                "title": {
                    "type": "string", 
                    "description": "Optional title for the object block."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description for the object block."
                },
                "fragment": {
                    "type": "string", 
                    "description": "Optional fragment identifier for the object block URI (e.g., 'intro' creates #intro)."
                },
                "mode": {
                    "type": "string",
                    "description": "Optional URI of the block mode. Defaults to ReadMode if not specified.",
                    "enum": [
                        "https://w3id.org/atomgraph/client#GraphMode",
                        "https://w3id.org/atomgraph/client#MapMode", 
                        "https://w3id.org/atomgraph/client#ChartMode",
                        "https://w3id.org/atomgraph/client#ReadMode"
                    ],
                    "default": "https://w3id.org/atomgraph/client#ReadMode"
                }
            },
            "required": ["url", "value"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates and appends an object block to a LinkedDataHub document
        
        :arguments: A dictionary containing:
            - `url`: URI of the document to append to
            - `value`: URI of the object resource to reference
            - `title`: Optional title
            - `description`: Optional description  
            - `fragment`: Optional fragment identifier
            - `mode`: Optional display mode URI
        :return: Result from POST operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("AddObjectBlock operation expects 'url' to be a string.")
        
        value: str = Operation.execute_json(self.settings, arguments["value"], self.context)
        if not isinstance(value, str):
            raise ValueError("AddObjectBlock operation expects 'value' to be a string.")
        
        title = arguments.get("title")
        if title:
            title = Operation.execute_json(self.settings, title, self.context)
            if not isinstance(title, str):
                raise ValueError("AddObjectBlock operation expects 'title' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("AddObjectBlock operation expects 'description' to be a string.")
        
        fragment = arguments.get("fragment")
        if fragment:
            fragment = Operation.execute_json(self.settings, fragment, self.context)
            if not isinstance(fragment, str):
                raise ValueError("AddObjectBlock operation expects 'fragment' to be a string.")
        
        mode = arguments.get("mode")
        if mode:
            mode = Operation.execute_json(self.settings, mode, self.context)
            if not isinstance(mode, str):
                raise ValueError("AddObjectBlock operation expects 'mode' to be a string.")
        
        logging.info(f"Creating object block for document <%s> with value <%s>", url, value)
        
        # Step 1: Get current document to find next sequence number
        get_op = GET(settings=self.settings, context=self.context)
        doc = get_op.execute({
            "url": url
        })

        # Step 2: Extract sequence numbers from rdf:_N properties in JSON-LD list
        sequence_numbers = []
        if isinstance(doc, list):
            for resource in doc:
                 if resource.get("@id") == url:
                    # Look for rdf:_N properties  
                    for key in resource.keys():
                        if key.startswith("http://www.w3.org/1999/02/22-rdf-syntax-ns#_"):
                            # Extract the sequence number from the property URI
                            seq_num = key.split("#_")[-1]
                            try:
                                sequence_numbers.append(int(seq_num))
                            except ValueError:
                                continue
                    break
        else:
            raise ValueError("Expected a list of resources from GET operation, got: %s", type(doc))
        
        # Step 3: Determine next sequence number
        next_sequence = max(sequence_numbers, default=0) + 1
        sequence_property = f"http://www.w3.org/1999/02/22-rdf-syntax-ns#_{next_sequence}"
        
        logging.info(f"Next sequence number: {next_sequence}")
        
        # Step 4: Create subject URI (fragment or blank node)
        if fragment:
            block_id = f"{url}#{fragment}"
        else:
            block_id = "_:object-block"
        
        # Step 5: Build JSON-LD structure for the object block
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "ac": "https://w3id.org/atomgraph/client#"
            },
            "@id": url
        }
        
        # Add the object block resource
        block = {
            "@id": block_id,
            "@type": "ldh:Object",
            "rdf:value": {
                "@id": value
            }
        }
        
        # Add optional properties to object block
        if title:
            block["dct:title"] = title
        
        if description:
            block["dct:description"] = description
            
        if mode:
            block["ac:mode"] = {
                "@id": mode
            }
        
        # Add object block to the data structure
        data[sequence_property] = block
        
        logging.info(f"Posting object block with JSON-LD data: {data}")
        
        # Step 6: POST the JSON-LD content to the target URI
        return super().execute({
            "url": url,
            "data": data
        })
