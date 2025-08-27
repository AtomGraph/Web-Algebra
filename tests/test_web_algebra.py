#!/usr/bin/env python3
"""
Web Algebra Test Suite - W3C Style with Pytest

Flat structure with descriptive naming:
- positive/: PositiveExecutionTest - should succeed with expected JSON output
- negative/: NegativeExecutionTest - should fail with expected exception

Test file format:
{
  "name": "Test description", 
  "operation": { "@op": "...", "args": {...} },
  "expected": <json_result>  // for positive tests
  "expected_error": "TypeError"  // for negative tests
}
"""

import pytest
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import web_algebra.operations
from web_algebra.operation import Operation
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses
from web_algebra.json_result import JSONResult
import rdflib

class TestWebAlgebra:
    """W3C-style Web Algebra test suite"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        # Register all operations
        def register(classes):
            for cls in classes:
                Operation.register(cls)
        
        register(list_operation_subclasses(web_algebra.operations, Operation))
        
        # Setup settings (with and without auth)
        cls.settings = LinkedDataHubSettings()
        cls.settings_with_auth = LinkedDataHubSettings(
            cert_pem_path=os.getenv("CERT_PEM_PATH"),
            cert_password=os.getenv("CERT_PASSWORD")
        )
    
    def result_to_json(self, result: Any) -> Any:
        """Convert Web Algebra result to JSON for comparison"""
        # Handle JSONResult first (most specific)
        if isinstance(result, JSONResult):
            # Use the built-in to_json() method
            return result.to_json()
        # Handle RDFLib terms
        elif isinstance(result, (rdflib.URIRef, rdflib.Literal, rdflib.BNode)):
            return str(result)
        elif isinstance(result, rdflib.Graph):
            # Serialize as JSON-LD
            try:
                jsonld_str = result.serialize(format='json-ld')
                if isinstance(jsonld_str, bytes):
                    jsonld_str = jsonld_str.decode('utf-8')
                return json.loads(jsonld_str)
            except Exception:
                # Fallback to turtle for debugging
                return {"error": "Could not serialize to JSON-LD", 
                       "turtle": result.serialize(format='turtle')}
        elif isinstance(result, list):
            return [self.result_to_json(item) for item in result]
        elif isinstance(result, dict):
            return {k: self.result_to_json(v) for k, v in result.items()}
        else:
            return str(result)
    
    
    def choose_settings(self, test_file_name: str):
        """Choose appropriate settings based on test name"""
        if "ldh-" in test_file_name.lower() or "linkeddatahub" in test_file_name.lower():
            return self.settings_with_auth
        return self.settings
    
    @pytest.mark.parametrize("test_file", sorted(Path("positive").glob("*.json")))
    def test_positive_execution(self, test_file: Path):
        """PositiveExecutionTest - should succeed with expected output"""
        # Skip if file doesn't exist (e.g., test discovery issues)
        if not test_file.exists():
            pytest.skip(f"Test file {test_file} not found")
            
        # Load test data
        with open(test_file, 'r') as f:
            test_data = json.load(f)
        
        test_name = test_data.get("name", test_file.name)
        
        # Skip LinkedDataHub tests if no credentials
        if ("ldh-" in test_file.name or "linkeddatahub" in test_file.name):
            if not (os.getenv("CERT_PEM_PATH") and os.getenv("CERT_PASSWORD")):
                pytest.skip(f"LinkedDataHub test {test_name} requires CERT_PEM_PATH and CERT_PASSWORD")
        
        # Choose appropriate settings
        settings = self.choose_settings(test_file.name)
        
        # Execute operation
        try:
            result = Operation.process_json(settings, test_data["operation"])
        except Exception as e:
            # For external service tests, network failures are acceptable
            if any(service in test_file.name.lower() for service in ['dbpedia', 'wikidata', 'external']):
                if any(err in str(e).lower() for err in ['timeout', 'connection', 'network', 'http', '403', '404']):
                    pytest.xfail(f"External service test {test_name} failed due to network: {e}")
            raise AssertionError(f"Test {test_name} failed: {e}")
        
        # Compare with expected result if provided
        if "expected" in test_data:
            actual_json = self.result_to_json(result)
            expected_json = test_data["expected"]
            
            assert actual_json == expected_json, (
                f"Test {test_name} output mismatch:\\n"
                f"Expected: {json.dumps(expected_json, indent=2)}\\n"
                f"Actual:   {json.dumps(actual_json, indent=2)}"
            )
    
    @pytest.mark.parametrize("test_file", sorted(Path("negative").glob("*.json")))
    def test_negative_execution(self, test_file: Path):
        """NegativeExecutionTest - should fail with expected error"""
        # Skip if file doesn't exist
        if not test_file.exists():
            pytest.skip(f"Test file {test_file} not found")
            
        # Load test data  
        with open(test_file, 'r') as f:
            test_data = json.load(f)
        
        test_name = test_data.get("name", test_file.name)
        expected_error = test_data.get("expected_error", "Exception")
        
        # Get exception class
        try:
            if expected_error in ["Exception", "TypeError", "ValueError", "KeyError"]:
                exception_class = getattr(__builtins__, expected_error)
            else:
                # Try to import from common modules
                exception_class = Exception  # fallback
        except:
            exception_class = Exception
        
        # Choose appropriate settings
        settings = self.choose_settings(test_file.name)
        
        # Execute and expect failure
        with pytest.raises(exception_class) as exc_info:
            Operation.process_json(settings, test_data["operation"])
        
        # Ensure error message is not empty
        assert str(exc_info.value), f"Test {test_name} should have non-empty error message"


if __name__ == "__main__":
    """Run tests directly"""
    import subprocess
    subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])