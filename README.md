# WebAlgebra

A composable RDF operations system that translates natural language instructions into JSON-formatted domain-specific language operations for loading, querying, and writing RDF Linked Data.

## Overview

This system implements generic operations for RDF Linked Data and SPARQL management, as well as some LinkedDataHub-specific operations. Operations can be consumed in two ways:

1. **Executable JSON format**: Operations are composed into JSON structures and executed by the provided execution engine
2. **Model Context Protocol (MCP)**: Operations are exposed as tools for AI agents to use interactively

## Architecture

The system is built around the `Operation` abstract base class that provides:
- **Registry System**: Auto-discovery of operations from `src/web_algebra/operations/`
- **JSON DSL**: Operations use `@op` key with `args` for parameters, supporting nested operation calls
- **Execution Engine**: Both standalone execution and MCP server integration
- **Context System**: ForEach operations set row context for inner operations

### Key Components

- **[System Prompt](prompts/system.md)**: Complete operation definitions and JSON format specification
- **[Operation Interface](src/web_algebra/operation.py)**: Base class and JSON interpreter
- **[Operation Implementations](src/web_algebra/operations/)**: Directory containing all available operations
- **[JSON Examples](examples/)**: Sample operation compositions

## Usage

### Pre-requisites

1. [Install Poetry](https://python-poetry.org/docs/#installation)
2. ```bash
   poetry install
   ```

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
  --cert_password **********
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

#### Claude Desktop tool config

Add Web Algebra entry to the `mcpServer` configuration your `claude_desktop_config.json` file:
```json
{
    "mcpServers": {
        "Web Algebra": {
            "command": "uv",
            "args": [
                "run",
                "--with",
                "mcp[cli]",
                "--with",
                "rdflib",
                "--with",
                "openai",
                "python",
                "/Users/Martynas.Jusevicius/WebRoot/Web-Algebra/src/web_algebra/__main__.py"
            ],
            "env": {
                "PYTHONPATH": "/Users/Martynas.Jusevicius/WebRoot/Web-Algebra/src"
            }
        }
    }
}
```
