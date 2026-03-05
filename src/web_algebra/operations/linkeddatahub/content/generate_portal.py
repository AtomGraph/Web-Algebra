from rdflib import URIRef, Literal, Namespace
from rdflib.namespace import XSD
from rdflib.query import Result
from web_algebra.operation import Operation
from web_algebra.operations.schema.extract_ontology import ExtractOntology
from web_algebra.operations.linkeddatahub.content.generate_ontology_views import GenerateOntologyViews
from web_algebra.operations.linkeddatahub.content.generate_package_stylesheet import GeneratePackageStylesheet
from web_algebra.operations.linkeddatahub.content.generate_package_metadata import GeneratePackageMetadata
from web_algebra.operations.linkeddatahub.content.generate_class_containers import GenerateClassContainers
from web_algebra.operations.linkeddatahub.install_package import InstallPackage
from web_algebra.operations.linkeddatahub.upload_file import UploadFile
from web_algebra.operations.linkeddatahub.create_item import CreateItem
from web_algebra.operations.linkeddatahub.add_generic_service import AddGenericService
from web_algebra.json_result import JSONResult


class GeneratePortal(Operation):
    """Generates a complete LinkedDataHub portal from a SPARQL endpoint.

    Composes:
    1. ExtractOntology - extracts classes and properties from SPARQL endpoint
    2. GenerateOntologyViews - generates property views and writes package ontology (ns.ttl)
    3. GeneratePackageStylesheet - writes package stylesheet (layout.xsl) with suppression templates
    4. GeneratePackageMetadata - writes package metadata (package.ttl) with ldt:ontology and ac:stylesheet
    5. UploadFile - uploads package files (ns.ttl, layout.xsl, package.ttl) to LinkedDataHub
    6. InstallPackage - installs package via LinkedDataHub's /packages/install endpoint
    7. GenerateClassContainers - creates containers for each class with instance views

    The package files are uploaded to LinkedDataHub and hosted there, avoiding SSRF protection issues.
    """

    @classmethod
    def description(cls) -> str:
        return "Generates a complete LinkedDataHub portal with class containers and property views from a SPARQL endpoint"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "SPARQL endpoint to extract ontology from"},
                "package_name": {"type": "string", "description": "Package identifier (e.g., 'my-portal')"},
                "package_namespace": {"type": "string", "description": "Namespace URI for building service/query/view URIs"},
                "admin_base": {"type": "string", "description": "LinkedDataHub admin base URI (e.g., 'https://admin.localhost:4443/')"},
                "parent_container": {"type": "string", "description": "URI of parent container for class containers"},
                "files_container": {"type": "string", "description": "Container URI for uploading package files (e.g., 'https://localhost:4443/files/')"},
                "services_container": {"type": "string", "description": "Container URI for creating service resources (e.g., 'https://localhost:4443/services/')"},
            },
            "required": ["endpoint", "package_name", "package_namespace", "admin_base", "parent_container", "files_container", "services_container"],
        }

    def execute(self, endpoint: URIRef, package_name: str, package_namespace: URIRef,
                admin_base: URIRef, parent_container: URIRef, files_container: URIRef,
                services_container: URIRef) -> Result:
        """Generate complete portal by composing extraction and generation operations

        Args:
            endpoint: SPARQL endpoint URI
            package_name: Package identifier (e.g., 'my-portal')
            package_namespace: Namespace URI for building service/query/view URIs
            admin_base: LinkedDataHub admin base URI
            parent_container: URI of parent container for class containers
            files_container: Container URI for uploading package files
            services_container: Container URI for creating service resources

        Returns:
            Concatenated Result containing all operation results
        """
        import logging
        from pathlib import Path
        from rdflib import Graph, RDF
        from rdflib.namespace import DCTERMS

        # Set up paths for temporary local package files
        package_path = f"./packages/{package_name}"

        logging.info(f"Generating portal package '{package_name}'")
        logging.info(f"Package path: {package_path}")

        # Step 1: Extract ontology from SPARQL endpoint
        logging.info(f"Extracting ontology from endpoint {endpoint}")
        ontology_graph = ExtractOntology(settings=self.settings, context=self.context).execute(endpoint)

        # Step 2: Create service resource for queries
        ns = Namespace(package_namespace)
        service_uri = ns["Service"]

        logging.info(f"Creating service resource at {service_uri}")
        service_graph = Graph()
        SD = Namespace("http://www.w3.org/ns/sparql-service-description#")

        service_graph.add((service_uri, RDF.type, SD.Service))
        service_graph.add((service_uri, DCTERMS.title, Literal("SPARQL Service", datatype=XSD.string)))
        service_graph.add((service_uri, SD.endpoint, endpoint))
        service_graph.add((service_uri, SD.supportedLanguage, SD.SPARQL11Query))
        service_graph.add((service_uri, SD.supportedLanguage, SD.SPARQL11Update))

        # Step 3: Generate package ontology file (ns.ttl) with property views
        logging.info(f"Generating package ontology with property views")
        views_graph = GenerateOntologyViews(settings=self.settings, context=self.context).execute(
            ontology_graph, package_namespace, service_uri, package_path
        )

        # Step 4: Generate package stylesheet (layout.xsl)
        logging.info(f"Generating package stylesheet")
        stylesheet_result = GeneratePackageStylesheet(settings=self.settings, context=self.context).execute(
            views_graph, package_path
        )

        # Step 5: Upload package files to LinkedDataHub
        logging.info("Uploading package files to LinkedDataHub")

        # Upload ontology file (ns.ttl) with explicit content type
        logging.info("Uploading ns.ttl")
        ontology_upload = UploadFile(settings=self.settings, context=self.context).execute(
            files_container,
            f"{package_path}/ns.ttl",
            f"{package_name}-ns",
            f"{package_name} Ontology",
            content_type="text/turtle"
        )
        ontology_uri = ontology_upload.bindings[0]["file_uri"]

        # Upload stylesheet file (layout.xsl) with explicit content type
        logging.info("Uploading layout.xsl")
        stylesheet_upload = UploadFile(settings=self.settings, context=self.context).execute(
            files_container,
            f"{package_path}/layout.xsl",
            f"{package_name}-layout",
            f"{package_name} Stylesheet",
            content_type="text/xsl"
        )
        stylesheet_uri = stylesheet_upload.bindings[0]["file_uri"]

        # Generate package metadata (package.ttl) with LinkedDataHub-hosted URIs
        # Use relative URI #this for the package resource itself
        package_uri = URIRef("#this")

        logging.info(f"Generating package metadata")
        metadata_graph = GeneratePackageMetadata(settings=self.settings, context=self.context).execute(
            package_path, package_uri, ontology_uri, stylesheet_uri, package_name
        )

        # Upload package metadata file (package.ttl) with explicit content type
        logging.info("Uploading package.ttl")
        package_upload = UploadFile(settings=self.settings, context=self.context).execute(
            files_container,
            f"{package_path}/package.ttl",
            f"{package_name}-package",
            f"{package_name} Package Metadata",
            content_type="text/turtle"
        )

        # Use the actual file URI (with #this fragment) for package installation
        package_file_uri = package_upload.bindings[0]["file_uri"]
        package_uri_with_fragment = URIRef(f"{package_file_uri}#this")

        # Step 6: Install package via LinkedDataHub
        logging.info(f"Installing package via {admin_base}/packages/install")
        install_result = InstallPackage(settings=self.settings, context=self.context).execute(
            admin_base, package_uri_with_fragment
        )

        # Step 6.5: Create global SPARQL service resource
        logging.info("Creating global SPARQL service resource")

        # Create service document under services/ container
        # Use package_name as slug if available, otherwise fall back to "portal"
        service_slug = package_name if package_name else "portal"
        service_doc_result = CreateItem(settings=self.settings, context=self.context).execute(
            services_container,
            Literal(f"{package_name} SPARQL Service", datatype=XSD.string),
            Literal(service_slug, datatype=XSD.string)
        )
        service_doc_uri = service_doc_result.bindings[0]["url"]
        logging.info(f"Created service document at {service_doc_uri}")

        # Add service metadata to document with fragment #this
        service_fragment = "this"
        service_metadata_result = AddGenericService(settings=self.settings, context=self.context).execute(
            url=service_doc_uri,
            endpoint=endpoint,
            title=Literal("SPARQL Service", datatype=XSD.string),
            fragment=Literal(service_fragment, datatype=XSD.string)
        )

        # Service URI is document + fragment #this
        service_uri = URIRef(f"{service_doc_uri}#{service_fragment}")
        logging.info(f"Created service resource at {service_uri}")

        # Step 7: Generate class containers with global service
        logging.info(f"Generating class containers")
        class_containers_result = GenerateClassContainers(settings=self.settings, context=self.context).execute(
            ontology_graph, parent_container, endpoint, service_uri
        )

        # Concatenate all results
        all_bindings = []
        all_vars = set()

        # Add stylesheet result (JSONResult)
        all_bindings.extend(stylesheet_result.bindings)
        all_vars.update(stylesheet_result.vars)

        # Add install result (JSONResult)
        all_bindings.extend(install_result.bindings)
        all_vars.update(install_result.vars)

        # Add class containers result (JSONResult)
        all_bindings.extend(class_containers_result.bindings)
        all_vars.update(class_containers_result.vars)

        logging.info(f"Portal generation complete!")

        return JSONResult(list(all_vars), all_bindings)

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with strict type checking"""
        # Process endpoint
        endpoint_uri = Operation.process_json(
            self.settings, arguments["endpoint"], self.context, variable_stack
        )
        if not isinstance(endpoint_uri, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'endpoint' to be URIRef, got {type(endpoint_uri)}"
            )

        # Process package_name
        package_name_data = Operation.process_json(
            self.settings, arguments["package_name"], self.context, variable_stack
        )
        if not isinstance(package_name_data, (str, Literal)):
            raise TypeError(
                f"GeneratePortal operation expects 'package_name' to be string, got {type(package_name_data)}"
            )
        if isinstance(package_name_data, Literal):
            package_name_data = str(package_name_data)

        # Process package_namespace
        package_namespace_uri = Operation.process_json(
            self.settings, arguments["package_namespace"], self.context, variable_stack
        )
        if not isinstance(package_namespace_uri, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'package_namespace' to be URIRef, got {type(package_namespace_uri)}"
            )

        # Process admin_base
        admin_base_uri = Operation.process_json(
            self.settings, arguments["admin_base"], self.context, variable_stack
        )
        if not isinstance(admin_base_uri, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'admin_base' to be URIRef, got {type(admin_base_uri)}"
            )

        # Process parent_container
        parent_container_uri = Operation.process_json(
            self.settings, arguments["parent_container"], self.context, variable_stack
        )
        if not isinstance(parent_container_uri, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'parent_container' to be URIRef, got {type(parent_container_uri)}"
            )

        # Process files_container
        files_container_uri = Operation.process_json(
            self.settings, arguments["files_container"], self.context, variable_stack
        )
        if not isinstance(files_container_uri, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'files_container' to be URIRef, got {type(files_container_uri)}"
            )

        # Process services_container
        services_container_uri = Operation.process_json(
            self.settings, arguments["services_container"], self.context, variable_stack
        )
        if not isinstance(services_container_uri, URIRef):
            raise TypeError(
                f"GeneratePortal operation expects 'services_container' to be URIRef, got {type(services_container_uri)}"
            )

        return self.execute(endpoint_uri, package_name_data, package_namespace_uri,
                           admin_base_uri, parent_container_uri, files_container_uri,
                           services_container_uri)
