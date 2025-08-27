#!/usr/bin/env python3
import os
import subprocess
import glob
import sys

def test_example(example_file):
    cmd = [
        "python", "src/web_algebra/main.py", 
        "--from-json", example_file,
        "--cert_pem_path", "../LinkedDataHub/ssl/owner/cert.pem",
        "--cert_password", "Marchius"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            return "PASS", "Success"
        else:
            # Extract meaningful error from stderr
            stderr_lines = result.stderr.split('\n')
            error_line = next((line for line in stderr_lines if 'Error' in line or 'Exception' in line), result.stderr.split('\n')[-2] if result.stderr else "Unknown error")
            return "FAIL", error_line.strip()
    except subprocess.TimeoutExpired:
        return "FAIL", "Timeout (>20s)"
    except Exception as e:
        return "FAIL", str(e)

def main():
    # Test both examples and tests directories
    test_files = []
    test_files.extend(sorted(glob.glob("./examples/*.json")))
    test_files.extend(sorted(glob.glob("./tests/*.json")))
    
    results = []
    
    print("Testing all examples and tests...")
    print("=" * 80)
    
    for test_file in test_files:
        test_name = os.path.basename(test_file)
        test_dir = "examples" if "/examples/" in test_file else "tests"
        print(f"Testing {test_dir}/{test_name}...", end=" ", flush=True)
        
        status, message = test_example(test_file)
        results.append((f"{test_dir}/{test_name}", status, message))
        
        print(f"{status}: {message}")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    
    pass_count = sum(1 for _, status, _ in results if status == "PASS")
    fail_count = len(results) - pass_count
    
    # Group by examples vs tests
    examples_results = [(name, status, msg) for name, status, msg in results if name.startswith("examples/")]
    tests_results = [(name, status, msg) for name, status, msg in results if name.startswith("tests/")]
    
    print("EXAMPLES:")
    examples_pass = sum(1 for _, status, _ in examples_results if status == "PASS")
    for name, status, message in examples_results:
        print(f"{status:4} | {name:40} | {message}")
    
    print(f"\nTESTS:")
    tests_pass = sum(1 for _, status, _ in tests_results if status == "PASS")
    for name, status, message in tests_results:
        print(f"{status:4} | {name:40} | {message}")
    
    print("=" * 80)
    print(f"EXAMPLES: {examples_pass}/{len(examples_results)} PASS ({examples_pass/len(examples_results)*100:.1f}%)")
    print(f"TESTS: {tests_pass}/{len(tests_results)} PASS ({tests_pass/len(tests_results)*100:.1f}%)")
    print(f"TOTAL: {pass_count} PASS, {fail_count} FAIL out of {len(results)}")
    print(f"Overall success rate: {pass_count/len(results)*100:.1f}%")

if __name__ == "__main__":
    main()