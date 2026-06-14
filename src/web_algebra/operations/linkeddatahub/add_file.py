from typing import Any, Optional
import logging
import mimetypes
import urllib.parse
from pathlib import Path

from mcp import types
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from rdflib.query import Result

from web_algebra.client import FileClient
from web_algebra.json_result import JSONResult
from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation


class AddFile(Operation, MCPTool):
    """RDF/POST a file to a LinkedDataHub document, returning the minted upload URI.

    The file's RDF description (`nfo:FileDataObject` + filename + MIME type +
    sha1 + title) is appended to the target document; the file bytes
    themselves are stored by LDH at `<base>/uploads/{sha1}` under its
    built-in upload namespace, independent of the target document's URI.

    Unlike the rest of the `ldh-Add*` family, this op does not subclass
    `POST` — file upload uses `multipart/form-data` with LDH's RDF/POST
    dialect rather than an N-triples body, so it carries its own
    `FileClient` instance instead of inheriting `LinkedDataClient` plumbing.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = FileClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,
        )

    @classmethod
    def name(cls):
        return "ldh-AddFile"

    @classmethod
    def description(cls) -> str:
        return """Adds a file to a LinkedDataHub document via multipart RDF/POST.

        Appends `a nfo:FileDataObject ; nfo:fileName ; dct:title ; ...`
        to the target document and stores the file bytes at
        `<base>/uploads/{sha1}` (LDH's built-in upload namespace).

        Arguments:
        - `url` — URI of the target document to add the file's description to.
        - `file` — absolute local file path. The bytes are read and streamed
          to the server.
        - `title` — human-readable title (`dct:title`).
        - `description` — optional description (`dct:description`).
        - `content_type` — optional MIME-type override; auto-detected from
          the file path if absent.

        Returns a result with `url` (the minted `<base>/uploads/{sha1}` URI
        the file resource is now addressable at) and `status` (HTTP status
        code) bindings.
        """

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target document URI to add the file's description to.",
                },
                "file": {
                    "type": "string",
                    "description": "Absolute local file path. The bytes are read and uploaded.",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the file (dct:title).",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description (dct:description).",
                },
                "content_type": {
                    "type": "string",
                    "description": "Optional MIME-type override; auto-detected from path if absent.",
                },
            },
            "required": ["url", "file", "title"],
        }

    def execute(
        self,
        url: URIRef,
        file_path: Literal,
        title: Literal,
        description: Optional[Literal] = None,
        content_type: Optional[Literal] = None,
    ) -> Result:
        """Pure function: RDF/POST a file from disk with RDFLib terms."""
        if not isinstance(url, URIRef):
            raise TypeError(
                f"AddFile.execute expects url to be URIRef, got {type(url)}"
            )
        if not isinstance(file_path, Literal):
            raise TypeError(
                f"AddFile.execute expects file_path to be Literal, got {type(file_path)}"
            )
        if not isinstance(title, Literal):
            raise TypeError(
                f"AddFile.execute expects title to be Literal, got {type(title)}"
            )
        if description is not None and not isinstance(description, Literal):
            raise TypeError(
                f"AddFile.execute expects description to be Literal or None, got {type(description)}"
            )
        if content_type is not None and not isinstance(content_type, Literal):
            raise TypeError(
                f"AddFile.execute expects content_type to be Literal or None, got {type(content_type)}"
            )

        path_str = str(file_path)
        with open(path_str, "rb") as f:
            body = f.read()

        ct: Optional[str] = str(content_type) if content_type is not None else None
        if ct is None:
            ct, _ = mimetypes.guess_type(path_str)
        if ct is None:
            ct = "application/octet-stream"

        url_str = str(url)
        logging.info(
            "RDF/POSTing file %s (%d bytes, %s) to <%s>",
            path_str, len(body), ct, url_str,
        )

        response, sha1 = self.client.add_file(
            target_url=url_str,
            file_body=body,
            content_type=ct,
            title=str(title),
            description=str(description) if description is not None else None,
            filename=Path(path_str).name,
        )

        # The minted file URI lives at `<scheme>://<host>/uploads/<sha1>`
        # regardless of which target document we RDF/POSTed to. Reconstruct
        # from the target URL's host so callers don't need to thread the
        # base URL through separately.
        parsed = urllib.parse.urlparse(url_str)
        file_uri = f"{parsed.scheme}://{parsed.netloc}/uploads/{sha1}"

        logging.info("AddFile status %s → <%s>", response.status, file_uri)

        return JSONResult(
            vars=["status", "url"],
            bindings=[
                {
                    "status": Literal(response.status, datatype=XSD.integer),
                    "url": URIRef(file_uri),
                }
            ],
        )

    def execute_json(self, arguments: dict, variable_stack: list = []) -> Result:
        """JSON execution: process arguments with strict type checking."""
        url_data = Operation.process_json(
            self.settings, arguments["url"], self.context, variable_stack
        )
        if not isinstance(url_data, URIRef):
            raise TypeError(
                f"ldh-AddFile expects 'url' to be URIRef, got {type(url_data)}"
            )

        file_data = Operation.process_json(
            self.settings, arguments["file"], self.context, variable_stack
        )
        file_literal = self.to_string_literal(file_data)

        title_data = Operation.process_json(
            self.settings, arguments["title"], self.context, variable_stack
        )
        title_literal = self.to_string_literal(title_data)

        description_literal: Optional[Literal] = None
        if "description" in arguments:
            description_data = Operation.process_json(
                self.settings, arguments["description"], self.context, variable_stack
            )
            description_literal = self.to_string_literal(description_data)

        content_type_literal: Optional[Literal] = None
        if "content_type" in arguments:
            content_type_data = Operation.process_json(
                self.settings, arguments["content_type"], self.context, variable_stack
            )
            content_type_literal = self.to_string_literal(content_type_data)

        return self.execute(
            url_data,
            file_literal,
            title_literal,
            description_literal,
            content_type_literal,
        )

    def mcp_run(self, arguments: dict, context: Any = None) -> Any:
        """MCP execution: plain args → plain results."""
        url = URIRef(arguments["url"])
        file_path = Literal(arguments["file"], datatype=XSD.string)
        title = Literal(arguments["title"], datatype=XSD.string)
        description = (
            Literal(arguments["description"], datatype=XSD.string)
            if "description" in arguments
            else None
        )
        content_type = (
            Literal(arguments["content_type"], datatype=XSD.string)
            if "content_type" in arguments
            else None
        )

        result = self.execute(url, file_path, title, description, content_type)
        url_binding = result.bindings[0]["url"]
        return [types.TextContent(type="text", text=f"File added: {url_binding}")]
