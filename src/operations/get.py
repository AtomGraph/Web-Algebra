import logging
from operation import Operation
from client import LinkedDataClient

class GET(Operation):
    """
    Fetch RDF data from a given URL and return it in Turtle format.

    :attr cert_pem_path: Path to the client certificate PEM file.
    :attr cert_password: Password for the client certificate.
    """
    
    cert_pem_path: str
    cert_password: str

    def __init__(self, context: dict = None, url: str = None):
        """
        Initialize the GET operation.
        :param context: Execution context.
        :param url: The JSON operation dict or direct URL string.
        """
        super().__init__(context)

        if url is None:
            raise ValueError("GET operation requires 'url' to be set.")
        
        self.url = url  # ✅ Might be a string or another operation

        # ✅ Ensure that credentials are set
        if not hasattr(self, "cert_pem_path") or not hasattr(self, "cert_password"):
            raise ValueError("GET operation requires 'cert_pem_path' and 'cert_password' to be set.")

        # ✅ Initialize the LinkedDataClient
        self.client = LinkedDataClient(
            cert_pem_path=self.cert_pem_path,
            cert_password=self.cert_password,
            verify_ssl=False  # Optionally disable SSL verification
        )

        logging.info("GET operation initialized.")

    def execute(self):
        """
        Fetch RDF data from the specified URL and return it as a Turtle string.
        :return: A string containing RDF data serialized in Turtle format.
        """
        logging.info(f"Executing GET operation with raw URL: {self.url}")

        # ✅ Resolve `url` dynamically
        resolved_url = self.resolve_arg(self.url)
        logging.info(f"Resolved URL: {resolved_url}")

        # ✅ Fetch RDF graph from the resolved URL
        logging.info(f"Fetching RDF data from {resolved_url}...")
        graph = self.client.get(resolved_url)  # Let exceptions propagate naturally
        turtle_data = graph.serialize(format="turtle")
        logging.info(f"Successfully fetched RDF data from {resolved_url}.")
        return turtle_data
