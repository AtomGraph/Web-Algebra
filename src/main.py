import argparse
from registry import OperationRegistry
from operations.resolve_uri import ResolveURI
from operations.get import GET


def main():
    # Parse script arguments
    parser = argparse.ArgumentParser(description="Operation Registry Setup")
    parser.add_argument(
        "--cert_pem_path",
        type=str,
        required=True,
        help="Path to the client certificate PEM file",
    )
    parser.add_argument(
        "--cert_password",
        type=str,
        required=True,
        help="Password for the client certificate",
    )
    args = parser.parse_args()

    # Initialize the registry
    registry = OperationRegistry()

    # Register operations explicitly
    registry.register("ResolveURI", ResolveURI())
    registry.register(
        "GET",
        GET(cert_pem_path=args.cert_pem_path, cert_password=args.cert_password)
    )

    # Example: Invoke ResolveURI
    resolve_args = {"base": "http://example.org/", "relative_uri": "resource"}
    print("ResolveURI result:", registry.invoke("ResolveURI", resolve_args))

    # Example: Invoke GET
    get_args = {"url": "https://localhost:4443/"}
    print("GET result:", registry.invoke("GET", get_args))


if __name__ == "__main__":
    main()
