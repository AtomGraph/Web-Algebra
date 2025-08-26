#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import all operations to populate registry
import web_algebra.operations
from web_algebra.operation import Operation
from web_algebra.main import LinkedDataHubSettings

# Test data with nested operations
test_data = {
    "@context": {
        "schema": "https://schema.org/"
    },
    "@id": {
        "@op": "Uri",
        "args": {
            "input": "https://example.org/test"
        }
    },
    "@type": "schema:Person",
    "schema:name": {
        "@op": "Str", 
        "args": {
            "input": "Test Person"
        }
    }
}

settings = LinkedDataHubSettings()

# Test what happens
try:
    result = Operation.process_json(settings, test_data)
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
    if hasattr(result, 'serialize'):
        print("Serialized:")
        print(result.serialize(format='json-ld').decode())
except Exception as e:
    print(f"Error: {e}")