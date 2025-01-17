from urllib.parse import urljoin
from operation import Operation
import uuid

class ResolveURI(Operation):
    def execute(self, base: str, relative_uri: str = '') -> str:
        """
        Resolve a relative URI against a base URI.
        If the slug string is provided, then it is used as the relative path,
        otherwise a random UUID value is used as the slug. The slug value will
        be URL-encoded if necessary.
        :param base: The base URI.
        :param relative_uri: The relative URI to resolve.
        :return: The resolved absolute URI as a string.
        """
        if not relative_uri:
            relative_uri = str(uuid.uuid4())

        return str(urljoin(base, relative_uri)) + '/'
