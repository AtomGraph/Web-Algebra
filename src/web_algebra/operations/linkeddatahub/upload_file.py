from typing import Any
import urllib.request
import mimetypes
from pathlib import Path
from rdflib import URIRef, Literal, Namespace
from rdflib.namespace import RDF, DCTERMS, FOAF
from web_algebra.operation import Operation
from web_algebra.json_result import JSONResult
from web_algebra.client import LinkedDataClient


class UploadFile(Operation):
    """Uploads a file to LinkedDataHub using RDF/POST multipart encoding.

    Creates a document resource with metadata and uploads the file content.
    The file is stored at a content-addressed URI based on its SHA1 hash.

    Uses HTTP PUT with multipart/form-data following RDF/POST parameter naming:
    - sb (subject blank node), su (subject URI)
    - pu (predicate URI), ol (object literal), ou (object URI), ob (object blank node)
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,
        )

    @classmethod
    def description(cls) -> str:
        return "Uploads a file to LinkedDataHub using RDF/POST multipart encoding"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "container": {
                    "type": "string",
                    "description": "Parent container URI (e.g., https://localhost:4443/files/)"
                },
                "file_path": {
                    "type": "string",
                    "description": "Local path to the file to upload"
                },
                "slug": {
                    "type": "string",
                    "description": "URL-safe identifier for the document (e.g., 'my-ontology')"
                },
                "title": {
                    "type": "string",
                    "description": "Human-readable title for the document and file"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description"
                },
                "content_type": {
                    "type": "string",
                    "description": "Optional media type (e.g., 'text/xsl', 'text/turtle'). If not provided, will be detected from file extension"
                }
            },
            "required": ["container", "file_path", "slug", "title"],
        }

    def execute(self, container: URIRef, file_path: str, slug: str,
                title: str, description: str = None, content_type: str = None) -> JSONResult:
        """Upload file to LinkedDataHub via RDF/POST multipart

        Args:
            container: Parent container URI (must end with /)
            file_path: Local path to file
            slug: URL-safe document identifier
            title: Document and file title
            description: Optional description
            content_type: Optional media type (e.g., 'text/xsl'). If not provided, detected from file extension

        Returns:
            JSONResult with document_uri and file_uri
        """
        import logging
        from urllib.parse import quote

        # Ensure container ends with /
        container_str = str(container).rstrip('/') + '/'

        # Construct target document URI
        encoded_slug = quote(slug, safe='')
        target_uri = f"{container_str}{encoded_slug}/"

        logging.info(f"Uploading {file_path} to {target_uri}")

        # Read file content
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_content = file_path_obj.read_bytes()
        file_name = file_path_obj.name

        # Use explicit content type if provided, otherwise detect from file extension
        if content_type is None:
            detected_type, _ = mimetypes.guess_type(file_name)
            content_type = detected_type if detected_type else "application/octet-stream"

        logging.info(f"File: {file_name}, Content-Type: {content_type}")

        # Build multipart form data using RDF/POST parameter naming
        boundary = "----WebAlgebraFormBoundary7MA4YWxkTrZu0gW"

        # Define namespaces for RDF/POST
        NFO = Namespace("http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#")
        SIOC = Namespace("http://rdfs.org/sioc/ns#")
        DH = Namespace("https://www.w3.org/ns/ldt/document-hierarchy#")

        parts = []

        # RDF/POST marker
        parts.append(self._make_part(boundary, "rdf", ""))

        # File resource (blank node 'file')
        parts.append(self._make_part(boundary, "sb", "file"))

        # File: nfo:fileName (predicate THEN file content)
        parts.append(self._make_part(boundary, "pu", str(NFO.fileName)))
        parts.append(self._make_file_part(boundary, "ol", file_name, file_content, content_type))

        # File: dct:title
        parts.append(self._make_part(boundary, "pu", str(DCTERMS.title)))
        parts.append(self._make_part(boundary, "ol", title))

        # File: rdf:type nfo:FileDataObject
        parts.append(self._make_part(boundary, "pu", str(RDF.type)))
        parts.append(self._make_part(boundary, "ou", str(NFO.FileDataObject)))

        if description:
            parts.append(self._make_part(boundary, "pu", str(DCTERMS.description)))
            parts.append(self._make_part(boundary, "ol", description))

        # Document resource (target URI)
        parts.append(self._make_part(boundary, "su", target_uri))

        # Document: dct:title
        parts.append(self._make_part(boundary, "pu", str(DCTERMS.title)))
        parts.append(self._make_part(boundary, "ol", title))

        # Document: rdf:type dh:Item
        parts.append(self._make_part(boundary, "pu", str(RDF.type)))
        parts.append(self._make_part(boundary, "ou", str(DH.Item)))

        # Document: foaf:primaryTopic -> file
        parts.append(self._make_part(boundary, "pu", str(FOAF.primaryTopic)))
        parts.append(self._make_part(boundary, "ob", "file"))

        # Document: sioc:has_container
        parts.append(self._make_part(boundary, "pu", str(SIOC.has_container)))
        parts.append(self._make_part(boundary, "ou", container_str))

        # Build complete body
        body = b"".join(parts) + f"--{boundary}--\r\n".encode('utf-8')

        # Create request
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Accept': 'text/turtle',
        }

        request = urllib.request.Request(
            target_uri,
            data=body,
            headers=headers,
            method='PUT'
        )

        try:
            response = self.client.opener.open(request)
            status = response.status
            response_url = response.geturl()

            logging.info(f"File upload status: {status}")
            logging.info(f"Document URI: {response_url}")

            # Query the document to get the actual file content URI
            # The document has foaf:primaryTopic pointing to the file resource
            # We need to fetch the file URI which will be at /uploads/{sha1}
            from rdflib import Graph

            metadata_request = urllib.request.Request(
                response_url,
                headers={'Accept': 'text/turtle'}
            )
            metadata_response = self.client.opener.open(metadata_request)
            metadata_graph = Graph()
            metadata_graph.parse(data=metadata_response.read(), format='turtle')

            # Find the file URI via foaf:primaryTopic
            NFO = Namespace("http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#")
            file_uris = list(metadata_graph.subjects(RDF.type, NFO.FileDataObject))

            if not file_uris:
                raise ValueError(f"Could not find file URI in uploaded document metadata")

            file_uri = file_uris[0]
            logging.info(f"File content URI: {file_uri}")

            return JSONResult(
                vars=["document_uri", "file_uri"],
                bindings=[
                    {
                        "document_uri": URIRef(response_url),
                        "file_uri": file_uri,
                    }
                ],
            )

        except urllib.error.HTTPError as e:
            logging.error(f"File upload failed with status {e.code}: {e.reason}")
            logging.error(f"Response body: {e.read().decode('utf-8')}")
            raise

    def _make_part(self, boundary: str, name: str, value: str) -> bytes:
        """Create a simple text form part"""
        part = f"--{boundary}\r\n"
        part += f'Content-Disposition: form-data; name="{name}"\r\n'
        part += "\r\n"
        part += f"{value}\r\n"
        return part.encode('utf-8')

    def _make_file_part(self, boundary: str, name: str, filename: str,
                       content: bytes, content_type: str) -> bytes:
        """Create a file upload form part"""
        part = f"--{boundary}\r\n".encode('utf-8')
        part += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode('utf-8')
        part += f'Content-Type: {content_type}\r\n'.encode('utf-8')
        part += b"\r\n"
        part += content
        part += b"\r\n"
        return part

    def execute_json(self, arguments: dict, variable_stack: list = []) -> JSONResult:
        """JSON execution: process arguments with type checking"""
        # Process container
        container_data = Operation.process_json(
            self.settings, arguments["container"], self.context, variable_stack
        )
        if not isinstance(container_data, URIRef):
            raise TypeError(
                f"UploadFile operation expects 'container' to be URIRef, got {type(container_data)}"
            )

        # Process file_path
        file_path_data = Operation.process_json(
            self.settings, arguments["file_path"], self.context, variable_stack
        )
        if not isinstance(file_path_data, (str, Literal)):
            raise TypeError(
                f"UploadFile operation expects 'file_path' to be string, got {type(file_path_data)}"
            )
        if isinstance(file_path_data, Literal):
            file_path_data = str(file_path_data)

        # Process slug
        slug_data = Operation.process_json(
            self.settings, arguments["slug"], self.context, variable_stack
        )
        if not isinstance(slug_data, (str, Literal)):
            raise TypeError(
                f"UploadFile operation expects 'slug' to be string, got {type(slug_data)}"
            )
        if isinstance(slug_data, Literal):
            slug_data = str(slug_data)

        # Process title
        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        if not isinstance(title_data, (str, Literal)):
            raise TypeError(
                f"UploadFile operation expects 'title' to be string, got {type(title_data)}"
            )
        if isinstance(title_data, Literal):
            title_data = str(title_data)

        # Process optional description
        description_data = None
        if "description" in arguments:
            description_data = Operation.process_json(
                self.settings, arguments["description"], self.context, variable_stack
            )
            if not isinstance(description_data, (str, Literal)):
                raise TypeError(
                    f"UploadFile operation expects 'description' to be string, got {type(description_data)}"
                )
            if isinstance(description_data, Literal):
                description_data = str(description_data)

        # Process optional content_type
        content_type_data = None
        if "content_type" in arguments:
            content_type_data = Operation.process_json(
                self.settings, arguments["content_type"], self.context, variable_stack
            )
            if not isinstance(content_type_data, (str, Literal)):
                raise TypeError(
                    f"UploadFile operation expects 'content_type' to be string, got {type(content_type_data)}"
                )
            if isinstance(content_type_data, Literal):
                content_type_data = str(content_type_data)

        return self.execute(container_data, file_path_data, slug_data,
                          title_data, description_data, content_type_data)
