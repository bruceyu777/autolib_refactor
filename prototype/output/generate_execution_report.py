#!/usr/bin/env python3
"""
Test Execution Order Report Generator

This script generates a JSON report showing test execution order and results.
Useful for CI/CD pipelines and test analysis.

Usage:
    python generate_execution_report.py

Output:
    - reports/execution_order.json - Test execution order with details
"""

import json
from pathlib import Path
import datetime
import re


def parse_test_log(log_file):
    """Parse test execution log to extract execution order and timing"""
    execution_data = []
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return execution_data
    
    test_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+ \[.*?\] Test started: (test_\S+)")
    result_pattern = re.compile(r"PASSED|FAILED|SKIPPED")
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    test_count = 0
    for i, line in enumerate(lines):
        if "Test started:" in line:
            test_count += 1
            # Extract test name from line
            match = re.search(r"Test started: (\S+)", line)
            if match:
                test_name = match.group(1)
                
                # Look ahead to find result
                result = "PASSED"  # Default
                for future_line in lines[i:i+100]:
                    if "PASSED" in future_line:
                        result = "PASSED"
                        break
                    elif "FAILED" in future_line or "ERROR" in future_line:
                        result = "FAILED"
                        break
                
                # Extract timestamp
                time_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                timestamp = time_match.group(1) if time_match else ""
                
                execution_data.append({
                    "order": test_count,
                    "test_name": test_name,
                    "result": result,
                    "timestamp": timestamp
                })
    
    return execution_data


def generate_report(output_dir="reports"):
    """Generate execution order report"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Read test execution log
    log_file = output_path / "test_execution.log"
    execution_data = parse_test_log(log_file)
    
    if not execution_data:
        print("No test execution data found")
        return
    
    # Create report
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_tests": len(execution_data),
        "tests": execution_data,
        "summary": {
            "passed": len([t for t in execution_data if t["result"] == "PASSED"]),
            "failed": len([t for t in execution_data if t["result"] == "FAILED"]),
            "skipped": len([t for t in execution_data if t["result"] == "SKIPPED"])
        }
    }
    
    # Save report
    report_file = output_path / "execution_order.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✓ Execution order report generated: {report_file}")
    print(f"  Total tests: {report['total_tests']}")
    print(f"  Passed: {report['summary']['passed']}")
    print(f"  Failed: {report['summary']['failed']}")
    print(f"  Skipped: {report['summary']['skipped']}")


if __name__ == "__main__":
    generate_report()
