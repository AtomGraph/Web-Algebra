# LinkedDataHub DSL operations

# Architecture

* GPT [system prompt](prompts/system.md)
  * operation definitions
  * JSON format specification ([JSON examples](examples))
* [`Operation` interface](src/operation.py)
  * JSON intepreter
* [Operation implementations](src/operations)

ChatGPT thread: https://chatgpt.com/c/679abd11-cc00-8009-8039-cecc0dd526e7

## Usage

### Standalone

```bash
poetry run python src/web_algebra/main.py --from-json ./examples/example.json
```

See [JSON examples](examples).

#### With LinkedDataHub

1. Run LinkedDataHub (ideally v5 from the `develop` branch)
2. Execute `src/web_algebra/main.py`, it expects the path to your LDH's owner certificate and its password as arguments. For example:

```bash
poetry run python src/web_algebra/main.py --from-json ./examples/denmark-cities.json \
  --cert_pem_path ../LinkedDataHub/ssl/owner/cert.pem \
  --cert_password Marchius
```
3. Enter instruction (see [examples](examples.md))

### As MCP server

stdio transport:
```bash
poetry run mcp dev src/web_algebra/__main__.py 
```

HTTP transport:
```bash
poetry run uvicorn web_algebra.server:server --reload
```
