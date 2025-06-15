# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is LinkedDataHub DSL - a composable RDF operations system that translates natural language instructions into JSON-formatted domain-specific language operations for loading, querying, and writing RDF data.

## Core Architecture

The system is built around the `Operation` abstract base class in `src/web_algebra/operation.py` which:
- Provides a registry system for all operations via `Operation.registry`
- Supports both standalone execution (`execute()`) and MCP server integration (`run()`)
- Handles recursive JSON execution with `execute_json()` that processes nested `@op` structures
- Operations are auto-discovered from `src/web_algebra/operations/` directory

### Key Components

- **Operation Registry**: Operations self-register via `Operation.register()` during module import
- **JSON DSL**: Operations use `@op` key with `args` for parameters, supporting nested operation calls
- **Context System**: ForEach operations set row context for inner operations to access via `Var`
- **RDF Integration**: Uses `rdflib.Graph` internally, JSON-LD for interchange

## Commands

### Development
```bash
# Install dependencies
poetry install

# Run standalone with JSON file
poetry run python src/web_algebra/main.py --from-json ./examples/example.json

# Run with LinkedDataHub integration
poetry run python src/web_algebra/main.py --from-json ./examples/denmark-cities.json \
  --cert_pem_path ../LinkedDataHub/ssl/owner/cert.pem \
  --cert_password Marchius

# Run as MCP server
poetry run uvicorn web_algebra.server:server --reload
```

### Operation Development

When adding new operations:
1. Inherit from `Operation` in `src/web_algebra/operation.py`
2. Implement required methods: `description()`, `inputSchema()`, `execute()`, `run()`
3. Place in `src/web_algebra/operations/` directory for auto-discovery
4. Use `@op` and `args` structure in JSON examples

### JSON DSL Format

Operations must follow this structure:
```json
{
  "@op": "OperationName",
  "args": {
    "parameter": "value",
    "nested_op": {
      "@op": "AnotherOperation", 
      "args": {...}
    }
  }
}
```

Key operations include: GET, POST, PUT, SELECT, CONSTRUCT, ForEach, Var, Str, ResolveURI, SPARQLString.

## Settings

The system uses `LinkedDataHubSettings` for certificate-based authentication with LinkedDataHub instances. MCP server configuration is in `src/web_algebra/server.py`.