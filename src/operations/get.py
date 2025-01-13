from client import LinkedDataClient
from operation import Operation

class GET(Operation):

    client: LinkedDataClient

    def __init__(self, cert_pem_path: str, cert_password: str):
        """
        Initialize the GET operation with a LinkedDataClient.
        :param cert_pem_path: Path to the client certificate PEM file.
        :param cert_password: Password for the client certificate.
        """
        self.client = LinkedDataClient(
            cert_pem_path=cert_pem_path,
            cert_password=cert_password,
            verify_ssl=False  # Optionally disable SSL verification
        )

    def execute(self, url: str) -> str:
        """
        Fetch RDF data from the specified URL and return it as a Turtle string.
        :param url: The URL to fetch RDF data from.
        :return: A string containing RDF data serialized in Turtle format.
        """
        # Fetch the RDF graph from the URL using the LinkedDataClient
        try:
            graph = self.client.get(url)
            # Serialize the RDF graph to Turtle format and return it
            return graph.serialize(format="turtle")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch RDF data from {url}: {str(e)}")
