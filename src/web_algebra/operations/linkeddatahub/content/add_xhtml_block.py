from typing import Any
import logging
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
                    "description": "The URI of the document to append the XHTML block to."
                },
                "value": {
                    "type": "string", 
                    "description": "XHTML content as canonical XML literal (must be well-formed XML)."
                },
                "title": {
                    "type": "string", 
                    "description": "Optional title for the XHTML block."
                },
                "description": {
                    "type": "string", 
                    "description": "Optional description for the XHTML block."
                },
                "fragment": {
                    "type": "string", 
                    "description": "Optional fragment identifier for the XHTML block URI (e.g., 'intro' creates #intro)."
                }
            },
            "required": ["url", "value"]
        }
    
    def execute(self, arguments: dict[str, str]) -> Any:
        """
        Creates and appends an XHTML block to a LinkedDataHub document
        
        :arguments: A dictionary containing:
            - `url`: URI of the document to append to
            - `value`: Canonical XML literal content
            - `title`: Optional title
            - `description`: Optional description  
            - `fragment`: Optional fragment identifier
        :return: Result from POST operation
        """
        url: str = Operation.execute_json(self.settings, arguments["url"], self.context)
        if not isinstance(url, str):
            raise ValueError("CreateXHTMLBlock operation expects 'url' to be a string.")
        
        value: str = Operation.execute_json(self.settings, arguments["value"], self.context)
        if not isinstance(value, str):
            raise ValueError("CreateXHTMLBlock operation expects 'value' to be a string.")
        
        title = arguments.get("title")
        if title:
            title = Operation.execute_json(self.settings, title, self.context)
            if not isinstance(title, str):
                raise ValueError("CreateXHTMLBlock operation expects 'title' to be a string.")
        
        description = arguments.get("description")
        if description:
            description = Operation.execute_json(self.settings, description, self.context)
            if not isinstance(description, str):
                raise ValueError("CreateXHTMLBlock operation expects 'description' to be a string.")
        
        fragment = arguments.get("fragment")
        if fragment:
            fragment = Operation.execute_json(self.settings, fragment, self.context)
            if not isinstance(fragment, str):
                raise ValueError("CreateXHTMLBlock operation expects 'fragment' to be a string.")
        
        logging.info(f"Creating XHTML block for document <%s>", url)
        
        # Step 1: Get current document to find next sequence number
        get_op = GET(settings=self.settings, context=self.context)
        doc = get_op.execute({
            "url": url
        })
        logging.info(f"DOC: %s", doc)

        # Step 2: Extract sequence numbers from rdf:_N properties in JSON-LD @graph
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
            block_id = "_:xhtml-block"
        
        # Step 5: Build JSON-LD structure for the XHTML block
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            },
            "@id": url
        }
        
        # Add the XHTML block resource
        block = {
            "@id": block_id,
            "@type": "ldh:XHTML",
            "rdf:value": {
                "@type": "rdf:XMLLiteral",
                "@value": value
            }
        }
        
        # Add optional properties to XHTML block
        if title:
            block["dct:title"] = title
        
        if description:
            block["dct:description"] = description
        
        # Add XHTML block to the data structure
        data[sequence_property] = block
        
        logging.info(f"Posting XHTML block with JSON-LD data: {data}")
        
        # Step 6: POST the JSON-LD content to the target URI
        return super().execute({
            "url": url,
            "data": data
        })
