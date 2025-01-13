# LinkedDataHub DSL operations

# Architecture

* [Operation registry](src/registry.py)
* [`Operation` interface](src/operation.py)
* Sample operation implementations ([`GET`](src/operations/get.py) and [`ResolveURI`](src/operations/resolve_uri.py) for now)

## Usage

1. Run LinkedDataHub (ideally v5 from the `develop` branch)
2. Execute `src/main.py`, it expects the path to your LDH's owner certificate and its password as arguments. For example:

```bash
python src/main.py --cert_pem_path ~/WebRoot/AtomGraph/LinkedDataHub/ssl/owner/cert.pem --cert_password ******
```

You should see Turtle output of the root document of LinkedDataHub - that is the result of a `GET(https://localhost:4443/)` operation call which is used as an example.
