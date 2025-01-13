from urllib.parse import urljoin
from operation import Operation

class ResolveURI(Operation):
    def execute(self, base: str, relative_uri: str) -> str:
        """
        Resolve a relative URI against a base URI.
        :param base: The base URI.
        :param relative_uri: The relative URI to resolve.
        :return: The resolved absolute URI as a string.
        """
        return str(urljoin(base, relative_uri))
