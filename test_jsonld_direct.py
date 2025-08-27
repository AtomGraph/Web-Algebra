#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from web_algebra.operation import Operation
from web_algebra.main import LinkedDataHubSettings

# Test what happens when a JSON-LD object with nested operations hits process_json()
jsonld_with_ops = {
    "@context": {
        "schema": "https://schema.org/"
    },
    "@id": {
        "@op": "URI",  # This nested operation should be processed
        "args": {
            "input": "https://example.org/person/1"
        }
    },
    "@type": "schema:Person", 
    "schema:name": {
        "@op": "Str",  # This nested operation should be processed
        "args": {
            "input": "John Doe"  
        }
    }
}

settings = LinkedDataHubSettings()

print("=== Testing JSON-LD object processing ===")
print("The JSON-LD object contains nested @op operations that should be processed.")
print("But since the object itself has no @op key, it goes to the JSON-LD path.")
print("The JSON-LD path does NOT process nested operations - it just converts to Graph.")
print("")

print("JSON-LD input:")
import json
print(json.dumps(jsonld_with_ops, indent=2))
print("")

print("Processing through Operation.process_json()...")
result = Operation.process_json(settings, jsonld_with_ops)

print(f"Result type: {type(result)}")
print("Serialized result:")
serialized = result.serialize(format='json-ld')
if isinstance(serialized, bytes):
    serialized = serialized.decode()
print(serialized)

print("\n=== Analysis ===")
print("Notice the @id and schema:name values are now blank nodes (_:N...)")
print("This proves the nested @op operations were NOT processed!")
print("They were treated as literal JSON-LD data and converted to blank nodes.")