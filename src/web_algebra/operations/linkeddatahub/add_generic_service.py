from typing import Any
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.operation import Operation
from web_algebra.operations.linked_data.post import POST


class AddGenericService(POST):
    @classmethod
    def name(cls):
        return "ldh-AddGenericService"

    @classmethod
    def description(cls) -> str:
        return """Appends a generic SPARQL service to a LinkedDataHub document using service description.
        
        This tool creates a SPARQL service description that can be referenced and used within LinkedDataHub.
        The service description includes endpoint information and supported capabilities.
        
        This tool:
        - Creates an sd:Service resource with endpoint URI and supported languages
        - Posts the new service description to the target document
        - Supports optional title, description, fragment identifier, graph store, and authentication
        - Automatically sets SPARQL 1.1 Query and Update support"""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URI of the document to append the service to.",
                },
                "endpoint": {
                    "type": "string",
                    "description": "Endpoint URI of the SPARQL service.",
                },
                "title": {"type": "string", "description": "Title of the service."},
                "description": {
                    "type": "string",
                    "description": "Optional description of the service.",
                },
                "fragment": {
                    "type": "string",
                    "description": "Optional fragment identifier for the service URI (e.g., 'my-service' creates #my-service).",
                },
                "graph_store": {
                    "type": "string",
                    "description": "Optional Graph Store URI for the service.",
                },
                "auth_user": {
                    "type": "string",
                    "description": "Optional authorization username for the service.",
                },
                "auth_pwd": {
                    "type": "string",
                    "description": "Optional authorization password for the service.",
                },
            },
            "required": ["url", "endpoint", "title"],
        }

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Any:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"AddGenericService operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        endpoint_data = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_data, URIRef):
            raise TypeError(
                f"AddGenericService operation expects 'endpoint' to be URIRef, got {type(endpoint_data)}"
            )

        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        title_literal = self.to_string_literal(title_data)

        # Process optional arguments
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

        graph_store_uri = None
        if "graph_store" in arguments:
            graph_store_data = Operation.process_json(
                self.settings, arguments["graph_store"], self.context, variable_stack
            )
            if not isinstance(graph_store_data, URIRef):
                raise TypeError(
                    f"AddGenericService operation expects 'graph_store' to be URIRef, got {type(graph_store_data)}"
                )
            graph_store_uri = graph_store_data

        auth_user_literal = None
        if "auth_user" in arguments:
            auth_user_data = Operation.process_json(
                self.settings, arguments["auth_user"], self.context, variable_stack
            )
            auth_user_literal = self.to_string_literal(auth_user_data)

        auth_pwd_literal = None
        if "auth_pwd" in arguments:
            auth_pwd_data = Operation.process_json(
                self.settings, arguments["auth_pwd"], self.context, variable_stack
            )
            auth_pwd_literal = self.to_string_literal(auth_pwd_data)

        return self.execute(
            url_data,
            endpoint_data,
            title_literal,
            description_literal,
            fragment_literal,
            graph_store_uri,
            auth_user_literal,
            auth_pwd_literal,
        )

    def execute(
        self,
        url: URIRef,
        endpoint: URIRef,
        title: Literal,
        description: Literal = None,
        fragment: Literal = None,
        graph_store: URIRef = None,
        auth_user: Literal = None,
        auth_pwd: Literal = None,
    ) -> Any:
        """Pure function: create SPARQL service description with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"AddGenericService.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(endpoint, URIRef):
            raise TypeError(
                f"AddGenericService.execute expects endpoint to be URIRef, got {type(endpoint)}"
            )
        if not isinstance(title, Literal) or title.datatype != XSD.string:
            raise TypeError(
                f"AddGenericService.execute expects title to be string Literal, got {type(title)}"
            )
        if description is not None and (
            not isinstance(description, Literal) or description.datatype != XSD.string
        ):
            raise TypeError(
                f"AddGenericService.execute expects description to be string Literal, got {type(description)}"
            )
        if fragment is not None and (
            not isinstance(fragment, Literal) or fragment.datatype != XSD.string
        ):
            raise TypeError(
                f"AddGenericService.execute expects fragment to be string Literal, got {type(fragment)}"
            )
        if graph_store is not None and not isinstance(graph_store, URIRef):
            raise TypeError(
                f"AddGenericService.execute expects graph_store to be URIRef, got {type(graph_store)}"
            )
        if auth_user is not None and (
            not isinstance(auth_user, Literal) or auth_user.datatype != XSD.string
        ):
            raise TypeError(
                f"AddGenericService.execute expects auth_user to be string Literal, got {type(auth_user)}"
            )
        if auth_pwd is not None and (
            not isinstance(auth_pwd, Literal) or auth_pwd.datatype != XSD.string
        ):
            raise TypeError(
                f"AddGenericService.execute expects auth_pwd to be string Literal, got {type(auth_pwd)}"
            )

        url_str = str(url)
        endpoint_str = str(endpoint)
        title_str = str(title)
        description_str = str(description) if description else None
        fragment_str = str(fragment) if fragment else None
        graph_store_str = str(graph_store) if graph_store else None
        auth_user_str = str(auth_user) if auth_user else None
        auth_pwd_str = str(auth_pwd) if auth_pwd else None

        logging.info(
            "Creating service description for document <%s> with endpoint <%s>",
            url_str,
            endpoint_str,
        )

        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment_str:
            subject_id = f"#{fragment_str}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"

        # Build JSON-LD structure for the service description - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dh": "https://www.w3.org/ns/ldt/document-hierarchy#",
                "a": "https://w3id.org/atomgraph/core#",
                "dct": "http://purl.org/dc/terms/",
                "foaf": "http://xmlns.com/foaf/0.1/",
                "sd": "http://www.w3.org/ns/sparql-service-description#",
            },
            "@id": subject_id,
            "@type": "sd:Service",
            "dct:title": title_str,
            "sd:endpoint": {"@id": endpoint_str},
            "sd:supportedLanguage": [
                {"@id": "sd:SPARQL11Query"},
                {"@id": "sd:SPARQL11Update"},
            ],
        }

        # Add optional properties - matching shell script conditional logic
        if graph_store_str:
            data["a:graphStore"] = {"@id": graph_store_str}

        if auth_user_str:
            data["a:authUser"] = auth_user_str

        if auth_pwd_str:
            data["a:authPwd"] = auth_pwd_str

        if description_str:
            data["dct:description"] = description_str

        logging.info(f"Posting service description with JSON-LD data: {data}")

        # POST the JSON-LD content to the target URI
        # Convert JSON-LD dict to Graph
        import json
        from rdflib import Graph

        graph = Graph()
        graph.parse(data=json.dumps(data), format="json-ld", base=url_str)
        return super().execute(url, graph)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        from mcp import types

        # Convert plain arguments to RDFLib terms
        url = URIRef(arguments["url"])
        endpoint = URIRef(arguments["endpoint"])
        title = Literal(arguments["title"], datatype=XSD.string)

        description = None
        if "description" in arguments:
            description = Literal(arguments["description"], datatype=XSD.string)

        fragment = None
        if "fragment" in arguments:
            fragment = Literal(arguments["fragment"], datatype=XSD.string)

        graph_store = None
        if "graph_store" in arguments:
            graph_store = URIRef(arguments["graph_store"])

        auth_user = None
        if "auth_user" in arguments:
            auth_user = Literal(arguments["auth_user"], datatype=XSD.string)

        auth_pwd = None
        if "auth_pwd" in arguments:
            auth_pwd = Literal(arguments["auth_pwd"], datatype=XSD.string)

        # Call pure function
        result = self.execute(
            url,
            endpoint,
            title,
            description,
            fragment,
            graph_store,
            auth_user,
            auth_pwd,
        )

        # Return status for MCP response
        status_binding = result.bindings[0]["status"]
        return [
            types.TextContent(type="text", text=f"Generic service added - status: {status_binding}")
        ]
