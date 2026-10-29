from typing import Any, Optional
import logging
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from web_algebra.operation import Operation
from web_algebra.operations.linkeddatahub.fragments import fragment_id
from web_algebra.operations.linked_data.post import POST


class AddView(POST):
    @classmethod
    def name(cls):
        return "ldh-AddView"

    @classmethod
    def description(cls) -> str:
        return """Writes a view of SPARQL SELECT query results to a LinkedDataHub document.
        The view is a resource the document holds, not one of its content blocks: to show it in the content mode,
        place it with ldh-AddObjectBlock, the view's URI as its value - so give the view a fragment identifier.
        
        A view shows resources - things, people, places, documents - each as itself: its label, its image,
        its links. LinkedDataHub DESCRIBEs the resources the query's first projected variable binds and renders
        those descriptions in the view's mode, so that variable must bind resources (SELECT ?thing WHERE { ... }).
        One that binds values - a name, a price, a computed total - describes nothing. To show values or
        aggregates (totals, counts, sums by month), use ldh-AddResultSetChart instead.

        A list of resources is a view even when what matters about them lives on related resources - a thing's
        shop and price on the order it came from, a message's sender on a person. Do not join those values into
        one table to show them beside each resource: select the resources, and let each one's own page show
        what it links to. Put values that summarise the related resources (spend per shop) in a chart beside it.

        This tool:
        - Creates an ldh:View resource linked to an existing sp:Select query resource
        - Configures optional display mode for the view
        - Posts the new view resource to the target document
        - Supports optional title, description, fragment identifier, and display mode

        Pick the mode by what the resources carry:
        - https://w3id.org/atomgraph/client#GridMode: a card per resource, led by its image. The fit for resources
          that have one (foaf:img, foaf:depiction, foaf:logo, schema:image, schema:logo, schema:thumbnailUrl):
          products, possessions, people, organizations
        - https://w3id.org/atomgraph/client#MapMode: a pin per resource that has geo:lat and geo:long. The fit for
          places, addresses, venues, shops
        - https://w3id.org/atomgraph/client#GraphMode: the resources and the links between them, as a network. The
          fit for showing how things connect (who owns what, what came from where)
        - https://w3id.org/atomgraph/client#ListMode: a labelled list; the default, for resources with no image or
          coordinates
        - https://w3id.org/atomgraph/client#TableMode: a row per resource, a column per property, for comparing
          many resources property by property
        - https://w3id.org/atomgraph/client#ReadMode: each resource's full description, for a few resources
        - https://w3id.org/atomgraph/client#ChartMode: the resources' properties charted

        Note: The query parameter must be a URI of an existing sp:Select resource, not a SPARQL query string."""

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URI of the document to write the view to.",
                },
                "query": {
                    "type": "string",
                    "description": "URI of an existing sp:Select query resource to visualize (not a SPARQL query string).",
                },
                "title": {"type": "string", "description": "Title of the view."},
                "description": {
                    "type": "string",
                    "description": "Optional description of the view.",
                },
                "fragment": {
                    "type": "string",
                    "description": "Optional fragment identifier for the view URI (e.g., 'my-view' creates #my-view).",
                },
                "mode": {
                    "type": "string",
                    "description": "Optional URI of the layout the view shows its results in (a view mode, not an object block's mode). Defaults to ListMode. Pick it by what the resources carry: GridMode for resources with an image, MapMode for ones with coordinates, GraphMode for how they link (see the tool description).",
                    "enum": [
                        "https://w3id.org/atomgraph/client#ListMode",
                        "https://w3id.org/atomgraph/client#TableMode",
                        "https://w3id.org/atomgraph/client#GridMode",
                        "https://w3id.org/atomgraph/client#ReadMode",
                        "https://w3id.org/atomgraph/client#GraphMode",
                        "https://w3id.org/atomgraph/client#MapMode",
                        "https://w3id.org/atomgraph/client#ChartMode",
                    ],
                },
                "show_when_empty": {
                    "type": "boolean",
                    "description": "Optional: whether the view is shown when its query returns no results (ldh:showWhenEmpty). LinkedDataHub shows it unless this is false.",
                },
            },
            "required": ["url", "query", "title"],
        }

    def execute_json(self, arguments: dict[str, str], variable_stack: list = None) -> Any:
        """JSON execution: process arguments and delegate to execute()"""
        # Process required arguments
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"AddView operation expects 'url' to be URIRef, got {type(url_data)}"
            )

        query_data = Operation.process_json(
            self.settings, arguments["query"], self.context, variable_stack
        )
        if not isinstance(query_data, URIRef):
            raise TypeError(
                f"AddView operation expects 'query' to be URIRef, got {type(query_data)}"
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

        mode_uri = None
        if "mode" in arguments:
            mode_data = Operation.process_json(
                self.settings, arguments["mode"], self.context, variable_stack
            )
            if not isinstance(mode_data, URIRef):
                raise TypeError(
                    f"AddView operation expects 'mode' to be URIRef, got {type(mode_data)}"
                )
            mode_uri = mode_data

        show_when_empty = None
        if "show_when_empty" in arguments:
            show_when_empty = Operation.json_to_rdflib(Operation.process_json(
                self.settings, arguments["show_when_empty"], self.context, variable_stack
            ))

        return self.execute(
            url_data,
            query_data,
            title_literal,
            description_literal,
            fragment_literal,
            mode_uri,
            show_when_empty,
        )

    def execute(
        self,
        url: URIRef,
        query: URIRef,
        title: Literal,
        description: Optional[Literal] = None,
        fragment: Optional[Literal] = None,
        mode: Optional[URIRef] = None,
        show_when_empty: Optional[Literal] = None,
    ) -> Any:
        """Pure function: create SPARQL result set view with RDFLib terms"""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"AddView.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(query, URIRef):
            raise TypeError(
                f"AddView.execute expects query to be URIRef, got {type(query)}"
            )
        if not Operation.is_string_compatible(title):
            raise TypeError(
                f"AddView.execute expects title to be string Literal, got {type(title)}"
            )
        if description is not None and (
            not Operation.is_string_compatible(description)
        ):
            raise TypeError(
                f"AddView.execute expects description to be string Literal, got {type(description)}"
            )
        if fragment is not None and (
            not Operation.is_string_literal(fragment)
        ):
            raise TypeError(
                f"AddView.execute expects fragment to be string Literal, got {type(fragment)}"
            )
        if mode is not None and not isinstance(mode, URIRef):
            raise TypeError(
                f"AddView.execute expects mode to be URIRef, got {type(mode)}"
            )

        if show_when_empty is not None and not (
            isinstance(show_when_empty, Literal) and show_when_empty.datatype == XSD.boolean
        ):
            raise TypeError(
                f"AddView.execute expects show_when_empty to be an xsd:boolean Literal, got {show_when_empty!r}"
            )

        url_str = str(url)
        query_str = str(query)
        title_str = Operation.jsonld_text(title)
        description_str = Operation.jsonld_text(description) if description else None
        fragment_str = fragment_id(fragment)
        mode_str = str(mode) if mode else None

        logging.info(
            "Creating View for document <%s> with sp:Select resource <%s>",
            url_str,
            query_str,
        )

        # Create subject URI (fragment or blank node) - matching shell script logic
        if fragment_str:
            subject_id = f"#{fragment_str}"  # relative URI that will be resolved against the request URI
        else:
            subject_id = "_:subject"

        # Build JSON-LD structure for the view - matching shell script output
        data = {
            "@context": {
                "ldh": "https://w3id.org/atomgraph/linkeddatahub#",
                "dct": "http://purl.org/dc/terms/",
                "spin": "http://spinrdf.org/spin#",
            },
            "@id": subject_id,
            "@type": "ldh:View",
            "dct:title": title_str,
            "spin:query": {"@id": query_str},
        }

        # Add optional properties - matching shell script conditional logic
        if description_str:
            data["dct:description"] = description_str

        if mode_str:
            # Add the ac: namespace to context when mode is used
            data["@context"]["ac"] = "https://w3id.org/atomgraph/client#"
            data["ac:mode"] = {"@id": mode_str}

        if show_when_empty is not None:
            data["ldh:showWhenEmpty"] = show_when_empty.toPython()

        logging.info(f"Posting View with JSON-LD data: {data}")

        # Convert the JSON-LD content to a Graph and POST to the target URI
        graph = self.to_graph(data, base=url_str)
        return super().execute(url, graph)

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results"""
        from mcp import types

        # Convert plain arguments to RDFLib terms
        url = URIRef(arguments["url"])
        query = URIRef(arguments["query"])
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

        show_when_empty = (
            Literal(bool(arguments["show_when_empty"])) if "show_when_empty" in arguments else None
        )

        # Call pure function
        result = self.execute(url, query, title, description, fragment, mode, show_when_empty)

        # Return status for MCP response
        status_binding = result.bindings[0]["status"]
        return [types.TextContent(type="text", text=f"View added - status: {status_binding}")]
