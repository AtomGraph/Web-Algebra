from rdflib import Graph, Literal, URIRef
from lxml import etree
from web_algebra.operation import Operation
from web_algebra.json_result import JSONResult


class GeneratePackageStylesheet(Operation):
    """Generates a LinkedDataHub package stylesheet (layout.xsl).

    Creates an XSLT stylesheet with empty templates that override/suppress
    rendering for properties that have views defined in the package ontology.
    """

    @classmethod
    def description(cls) -> str:
        return "Generates LinkedDataHub package stylesheet with suppression templates for property views"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology": {
                    "type": "object",
                    "description": "RDF graph containing property views (to determine which properties to suppress)"
                },
                "package_path": {
                    "type": "string",
                    "description": "Path to write the stylesheet as layout.xsl file"
                }
            },
            "required": ["ontology", "package_path"],
        }

    def execute(self, ontology: Graph, package_path: str) -> JSONResult:
        """Generate package stylesheet with suppression templates

        Args:
            ontology: RDF graph containing property views
            package_path: Directory path where layout.xsl will be written

        Returns:
            JSONResult with file path and success status
        """
        from pathlib import Path

        # Query ontology to find all properties with views
        # We'll generate empty templates for these to suppress default rendering
        query = """
        PREFIX ldh: <https://w3id.org/atomgraph/linkeddatahub#>

        SELECT DISTINCT ?property
        WHERE {
          ?property ldh:view ?view .
        }
        ORDER BY ?property
        """

        results = ontology.query(query)
        properties = [row.asdict()["property"] for row in results]

        # Generate XSLT stylesheet with suppression templates
        xslt_content = self._generate_xslt(properties, ontology)

        # Create package directory if it doesn't exist
        package_dir = Path(package_path)
        package_dir.mkdir(parents=True, exist_ok=True)

        # Write stylesheet file
        stylesheet_file = package_dir / "layout.xsl"
        stylesheet_file.write_text(xslt_content)

        # Return success result
        return JSONResult(
            ["file_path", "status"],
            [{"file_path": Literal(str(stylesheet_file)), "status": Literal("success")}]
        )

    def _generate_xslt(self, properties: list, ontology: Graph) -> str:
        """Generate XSLT stylesheet content with suppression templates using XML DOM

        Args:
            properties: List of property URIRefs to create suppression templates for
            ontology: RDF graph to extract namespace prefix bindings from

        Returns:
            XSLT stylesheet as string
        """
        # Define XSLT namespace
        XSL_NS = "http://www.w3.org/1999/XSL/Transform"
        XS_NS = "http://www.w3.org/2001/XMLSchema"
        BS2_NS = "http://graphity.org/xsl/bootstrap/2.3.2"

        # Create namespace map for XSLT root
        nsmap = {
            'xsl': XSL_NS,
            'xs': XS_NS,
            'bs2': BS2_NS,
        }

        # Add namespace prefixes from ontology for properties
        # Build a map of namespace URI -> prefix for properties we need
        ns_uris_needed = set()
        for prop in properties:
            if isinstance(prop, URIRef):
                ns_uri = self._get_namespace_uri(str(prop))
                if ns_uri:
                    ns_uris_needed.add(ns_uri)

        # Get prefix bindings from ontology
        for ns_uri in ns_uris_needed:
            # Try to find prefix from ontology's namespace manager
            prefix = None
            for p, uri in ontology.namespace_manager.namespaces():
                if str(uri) == ns_uri:
                    prefix = p
                    break

            if prefix and prefix not in nsmap:
                nsmap[prefix] = ns_uri

        # Create root stylesheet element
        root = etree.Element(
            f"{{{XSL_NS}}}stylesheet",
            version="3.0",
            nsmap=nsmap
        )
        root.set("exclude-result-prefixes", "#all")

        # Add comment
        comment = etree.Comment(" Empty templates to suppress rendering of properties with views ")
        root.append(comment)

        # Add suppression template for each property
        for prop in properties:
            if not isinstance(prop, URIRef):
                continue

            prop_str = str(prop)

            # Get namespace and local name
            ns_uri = self._get_namespace_uri(prop_str)
            local_name = self._get_local_name(prop_str)

            # Find prefix for this namespace
            prefix = None
            for p, uri in nsmap.items():
                if uri == ns_uri and p not in ('xsl', 'xs'):
                    prefix = p
                    break

            if not prefix:
                # Fallback if no prefix found - skip this property
                continue

            # Add comment for this property
            prop_comment = etree.Comment(f" Suppress {prop_str} ")
            root.append(prop_comment)

            # Create template element: <xsl:template match="prefix:localName" mode="bs2:PropertyList" priority="1"/>
            template = etree.SubElement(
                root,
                f"{{{XSL_NS}}}template",
                match=f"{prefix}:{local_name}",
                mode="bs2:PropertyList",
                priority="1"
            )

        # Serialize to string with pretty printing
        xslt_bytes = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )

        return xslt_bytes.decode('utf-8')

    def _get_namespace_uri(self, uri: str) -> str:
        """Extract namespace URI from property URI (everything before # or last /)"""
        if '#' in uri:
            return uri.rsplit('#', 1)[0] + '#'
        elif '/' in uri:
            return uri.rsplit('/', 1)[0] + '/'
        return uri

    def _get_local_name(self, uri: str) -> str:
        """Extract local name from URI (part after # or last /)"""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri

    def execute_json(self, arguments: dict, variable_stack: list = []) -> JSONResult:
        """JSON execution: process arguments with type checking"""
        # Process ontology graph
        ontology_data = Operation.process_json(
            self.settings, arguments["ontology"], self.context, variable_stack
        )

        if not isinstance(ontology_data, Graph):
            raise TypeError(
                f"GeneratePackageStylesheet operation expects 'ontology' to be Graph, got {type(ontology_data)}"
            )

        # Process package_path
        package_path_data = Operation.process_json(
            self.settings, arguments["package_path"], self.context, variable_stack
        )

        if not isinstance(package_path_data, (str, Literal)):
            raise TypeError(
                f"GeneratePackageStylesheet operation expects 'package_path' to be string, got {type(package_path_data)}"
            )

        # Convert Literal to string if needed
        if isinstance(package_path_data, Literal):
            package_path_data = str(package_path_data)

        return self.execute(ontology_data, package_path_data)
