from typing import Any
import urllib.parse
import urllib.request
from rdflib import URIRef, Literal
from rdflib.namespace import XSD
from web_algebra.operation import Operation
from web_algebra.json_result import JSONResult
from web_algebra.client import LinkedDataClient


class InstallPackage(Operation):
    """Installs a LinkedDataHub package using the official package installation endpoint.

    POSTs to {admin_base}/packages/install with form-urlencoded parameter 'package-uri'
    pointing to the package metadata file. LinkedDataHub will fetch and install the
    ontology and stylesheet files referenced in the package metadata.
    """

    def model_post_init(self, __context: Any) -> None:
        self.client = LinkedDataClient(
            cert_pem_path=getattr(self.settings, "cert_pem_path", None),
            cert_password=getattr(self.settings, "cert_password", None),
            verify_ssl=False,
        )

    @classmethod
    def description(cls) -> str:
        return "Installs a LinkedDataHub package via the /packages/install endpoint"

    @classmethod
    def inputSchema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "admin_base": {
                    "type": "string",
                    "description": "Base URI of LinkedDataHub admin application (e.g., https://localhost:4443/)"
                },
                "package_uri": {
                    "type": "string",
                    "description": "URI of the package metadata file (e.g., http://localhost:8000/packages/my-portal/package.ttl#this)"
                }
            },
            "required": ["admin_base", "package_uri"],
        }

    def execute(self, admin_base: URIRef, package_uri: URIRef) -> JSONResult:
        """Install package via LinkedDataHub's package installation endpoint

        Args:
            admin_base: Base URI of LinkedDataHub admin application
            package_uri: URI of the package metadata file with #this fragment

        Returns:
            JSONResult with installation status
        """
        import logging

        # Construct the installation endpoint URL
        # Admin base should already end with /, just append packages/install
        admin_base_str = str(admin_base)
        if admin_base_str.endswith('/'):
            install_url = f"{admin_base_str}packages/install"
        else:
            install_url = f"{admin_base_str}/packages/install"

        logging.info(f"Installing package from {package_uri} to {install_url}")

        # Prepare form-urlencoded data
        form_data = urllib.parse.urlencode({'package-uri': str(package_uri)})
        form_bytes = form_data.encode('utf-8')

        # Create request with form data
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/turtle',
        }

        request = urllib.request.Request(
            install_url,
            data=form_bytes,
            headers=headers,
            method='POST'
        )

        try:
            # Use the client's opener to handle SSL and authentication
            response = self.client.opener.open(request)
            status = response.status
            response_url = response.geturl()

            logging.info(f"Package installation status: {status}")

            return JSONResult(
                vars=["status", "url"],
                bindings=[
                    {
                        "status": Literal(status, datatype=XSD.integer),
                        "url": URIRef(response_url),
                    }
                ],
            )

        except urllib.error.HTTPError as e:
            logging.error(f"Package installation failed with status {e.code}: {e.reason}")
            logging.error(f"Response body: {e.read().decode('utf-8')}")
            raise

    def execute_json(self, arguments: dict, variable_stack: list = []) -> JSONResult:
        """JSON execution: process arguments with type checking"""
        # Process admin_base
        admin_base_data = Operation.process_json(
            self.settings, arguments["admin_base"], self.context, variable_stack
        )

        if not isinstance(admin_base_data, URIRef):
            raise TypeError(
                f"InstallPackage operation expects 'admin_base' to be URIRef, got {type(admin_base_data)}"
            )

        # Process package_uri
        package_uri_data = Operation.process_json(
            self.settings, arguments["package_uri"], self.context, variable_stack
        )

        if not isinstance(package_uri_data, URIRef):
            raise TypeError(
                f"InstallPackage operation expects 'package_uri' to be URIRef, got {type(package_uri_data)}"
            )

        return self.execute(admin_base_data, package_uri_data)
