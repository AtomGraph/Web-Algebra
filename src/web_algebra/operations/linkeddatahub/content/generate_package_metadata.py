from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, DCTERMS
from web_algebra.operation import Operation


class GeneratePackageMetadata(Operation):
    """Generates LinkedDataHub package metadata file (package.ttl).

    Creates an RDF document describing the package with links to the ontology
    and stylesheet files using ldt:ontology and ac:stylesheet properties.
    """

    @classmethod
    def description(cls) -> str:
        return "Generates LinkedDataHub package metadata with ldt:ontology and ac:stylesheet references"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to write the package metadata as package.ttl file"
                },
                "package_uri": {
                    "type": "string",
                    "description": "Web-accessible URI where package metadata will be hosted"
                },
                "ontology_uri": {
                    "type": "string",
                    "description": "Web-accessible URI for the ns.ttl file"
                },
                "stylesheet_uri": {
                    "type": "string",
                    "description": "Web-accessible URI for the layout.xsl file"
                },
                "package_name": {
                    "type": "string",
                    "description": "Human-readable package name"
                }
            },
            "required": ["package_path", "package_uri", "ontology_uri", "stylesheet_uri", "package_name"],
        }

    def execute(self, package_path: str, package_uri: URIRef, ontology_uri: URIRef,
                stylesheet_uri: URIRef, package_name: str) -> Graph:
        """Generate package metadata file

        Args:
            package_path: Directory path where package.ttl will be written
            package_uri: URI of the package resource (can be relative like URIRef("#this"))
            ontology_uri: URI pointing to the ns.ttl file
            stylesheet_uri: URI pointing to the layout.xsl file
            package_name: Human-readable package name

        Returns:
            RDF graph containing package metadata
        """
        from pathlib import Path

        # Define namespaces
        LAPP = Namespace("https://w3id.org/atomgraph/linkeddatahub/apps#")
        LDT = Namespace("https://www.w3.org/ns/ldt#")
        AC = Namespace("https://w3id.org/atomgraph/client#")

        # Create metadata graph with empty base to allow relative URIs
        g = Graph()
        g.bind("lapp", LAPP)
        g.bind("ldt", LDT)
        g.bind("ac", AC)
        g.bind("dct", DCTERMS)

        # Add package metadata (using relative URI #this)
        g.add((package_uri, RDF.type, LAPP.Package))
        g.add((package_uri, DCTERMS.title, Literal(package_name)))
        g.add((package_uri, LDT.ontology, ontology_uri))
        g.add((package_uri, AC.stylesheet, stylesheet_uri))

        # Create package directory if it doesn't exist
        package_dir = Path(package_path)
        package_dir.mkdir(parents=True, exist_ok=True)

        # Write metadata file
        metadata_file = package_dir / "package.ttl"
        metadata_file.write_text(g.serialize(format="turtle"))

        return g

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Graph:
        """JSON execution: process arguments with type checking"""
        # Process package_path
        package_path_data = Operation.process_json(
            self.settings, arguments["package_path"], self.context, variable_stack
        )

        if not isinstance(package_path_data, (str, Literal)):
            raise TypeError(
                f"GeneratePackageMetadata operation expects 'package_path' to be string, got {type(package_path_data)}"
            )

        # Convert Literal to string if needed
        if isinstance(package_path_data, Literal):
            package_path_data = str(package_path_data)

        # Process package_uri
        package_uri_data = Operation.process_json(
            self.settings, arguments["package_uri"], self.context, variable_stack
        )

        if not isinstance(package_uri_data, URIRef):
            raise TypeError(
                f"GeneratePackageMetadata operation expects 'package_uri' to be URIRef, got {type(package_uri_data)}"
            )

        # Process ontology_uri
        ontology_uri_data = Operation.process_json(
            self.settings, arguments["ontology_uri"], self.context, variable_stack
        )

        if not isinstance(ontology_uri_data, URIRef):
            raise TypeError(
                f"GeneratePackageMetadata operation expects 'ontology_uri' to be URIRef, got {type(ontology_uri_data)}"
            )

        # Process stylesheet_uri
        stylesheet_uri_data = Operation.process_json(
            self.settings, arguments["stylesheet_uri"], self.context, variable_stack
        )

        if not isinstance(stylesheet_uri_data, URIRef):
            raise TypeError(
                f"GeneratePackageMetadata operation expects 'stylesheet_uri' to be URIRef, got {type(stylesheet_uri_data)}"
            )

        # Process package_name
        package_name_data = Operation.process_json(
            self.settings, arguments["package_name"], self.context, variable_stack
        )

        if not isinstance(package_name_data, (str, Literal)):
            raise TypeError(
                f"GeneratePackageMetadata operation expects 'package_name' to be string, got {type(package_name_data)}"
            )

        # Convert Literal to string if needed
        if isinstance(package_name_data, Literal):
            package_name_data = str(package_name_data)

        return self.execute(package_path_data, package_uri_data, ontology_uri_data,
                           stylesheet_uri_data, package_name_data)
