#!/usr/bin/env python3
"""
Enhanced Test Execution Order Report Generator v2

This script generates an HTML report showing test execution order with actual test results
from pytest-html's tests.json data file.

Features:
- Reads actual test results and execution times from pytest-html
- Orders tests by execution sequence from .pytest-order.txt
- Shows pass/fail status from actual test results
- Displays execution timing information

Usage:
    python generate_execution_html_v2.py

Output:
    - reports/execution_order.html - Test execution order report with actual results
"""

import json
from pathlib import Path
from datetime import datetime


def extract_results_from_json(results_json_path):
    """Extract test results from conftest.py's test_results.json"""
    tests_data = {}
    
    if not results_json_path.exists():
        return tests_data
    
    try:
        with open(results_json_path, 'r') as f:
            data = json.load(f)
        
        # The structure is: {test_name: {outcome: 'PASSED', nodeid: '...'}}
        for test_name, test_info in data.items():
            if isinstance(test_info, dict):
                outcome = test_info.get('outcome', 'UNKNOWN').upper()
                tests_data[test_name] = {
                    'outcome': outcome,
                    'duration': 0  # Duration not tracked in this version
                }
        
        return tests_data
    
    except Exception as e:
        print(f"Warning: Could not read test_results.json: {e}")
        return {}


def generate_execution_html(order_file, output_file="reports/execution_order.html"):
    """
    Generate HTML report showing execution order with actual results
    
    Args:
        order_file: Path to .pytest-order.txt (defines execution order)
        output_file: Path to output HTML file
    """
    
    # Create output directory
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read execution order from .pytest-order.txt
    grp_order = {}
    grp_name = "unknown"
    
    if Path(order_file).exists():
        with open(order_file, 'r') as f:
            for line in f:
                line = line.strip()
                if 'from:' in line:
                    grp_name = line.split('from:')[1].strip()
                elif ':' in line and not line.startswith('#'):
                    parts = line.split(':')
                    if len(parts) == 2:
                        order, test_file = int(parts[0]), parts[1].strip()
                        grp_order[test_file.replace('.py', '')] = order
    
    # Try to extract actual test results from conftest.py's test_results.json
    results_json = output_path.parent / 'test_results.json'
    
    test_results = {}
    if results_json.exists():
        test_results = extract_results_from_json(results_json)
        print(f"✓ Extracted {len(test_results)} test results from conftest.py")
    else:
        print(f"⚠ No test_results.json found - showing static report")
    
    # Convert to JSON format for JavaScript
    grp_order_json = json.dumps(grp_order)
    test_results_json = json.dumps(test_results)
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Order Report</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            height: 100%;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }}
        
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 28px;
            border-bottom: 4px solid #667eea;
            padding-bottom: 15px;
        }}
        
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .metadata-item {{
            padding: 15px;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
        
        .metadata-item label {{
            font-weight: bold;
            color: #555;
            display: block;
            margin-bottom: 8px;
            font-size: 12px;
            text-transform: uppercase;
        }}
        
        .metadata-item value {{
            color: #667eea;
            font-size: 16px;
            font-weight: 600;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }}
        
        .summary-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            color: white;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .summary-card .number {{
            font-size: 32px;
            margin-bottom: 8px;
        }}
        
        .summary-card .label {{
            font-size: 13px;
            opacity: 0.9;
            text-transform: uppercase;
        }}
        
        .total {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .passed {{ background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); }}
        .failed {{ background: linear-gradient(135deg, #f44336 0%, #da190b 100%); }}
        .skipped {{ background: linear-gradient(135deg, #ff9800 0%, #e68900 100%); }}
        
        .controls {{
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        
        .control-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        .control-btn:hover {{
            background: #764ba2;
            transform: translateY(-2px);
        }}
        
        .control-btn.active {{
            background: #764ba2;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        
        .search-box {{
            padding: 10px 16px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            width: 100%;
            max-width: 300px;
        }}
        
        .search-box:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
            overflow-x: auto;
        }}
        
        thead {{
            background: #2c3e50;
            color: white;
        }}
        
        th {{
            padding: 15px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tbody tr {{
            transition: all 0.2s;
        }}
        
        tbody tr:hover {{
            background: #f8f9fa;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        
        .order {{
            font-weight: bold;
            color: #667eea;
            min-width: 40px;
            text-align: center;
            background: #f8f9fa;
            border-radius: 4px;
            display: inline-block;
            width: 40px;
            height: 40px;
            line-height: 40px;
        }}
        
        .test-name {{
            font-family: 'Courier New', monospace;
            color: #2c3e50;
            font-size: 14px;
        }}
        
        .status {{
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            text-align: center;
            min-width: 80px;
        }}
        
        .status.PASSED {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        
        .status.FAILED {{
            background: #ffebee;
            color: #c62828;
        }}
        
        .status.SKIPPED {{
            background: #fff3e0;
            color: #e65100;
        }}
        
        .status.UNKNOWN {{
            background: #f5f5f5;
            color: #666;
        }}
        
        .duration {{
            font-family: 'Courier New', monospace;
            text-align: right;
            color: #666;
            font-size: 13px;
        }}
        
        .note {{
            background: linear-gradient(135deg, #fff3cd 0%, #ffe6b3 100%);
            border-left: 4px solid #ffc107;
            padding: 16px;
            margin-top: 30px;
            border-radius: 6px;
            color: #856404;
        }}
        
        .note strong {{
            display: block;
            margin-bottom: 8px;
        }}
        
        .note code {{
            background: rgba(255,255,255,0.5);
            padding: 2px 6px;
            border-radius: 3px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #999;
            font-size: 12px;
        }}
        
        .no-data {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}
            
            h1 {{
                font-size: 20px;
            }}
            
            table {{
                font-size: 12px;
            }}
            
            th, td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Test Execution Order Report</h1>
        
        <div class="metadata">
            <div class="metadata-item">
                <label>Group File</label>
                <value>{grp_name}</value>
            </div>
            <div class="metadata-item">
                <label>Generated</label>
                <value>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</value>
            </div>
            <div class="metadata-item">
                <label>Report Type</label>
                <value>Execution Order</value>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card total">
                <div class="number" id="sum-total">0</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="summary-card passed">
                <div class="number" id="sum-passed">0</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card failed">
                <div class="number" id="sum-failed">0</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card skipped">
                <div class="number" id="sum-skipped">0</div>
                <div class="label">Skipped</div>
            </div>
        </div>
        
        <div class="controls">
            <button class="control-btn active" onclick="filterTests('ALL')">All</button>
            <button class="control-btn" onclick="filterTests('PASSED')">Passed</button>
            <button class="control-btn" onclick="filterTests('FAILED')">Failed</button>
            <input type="text" class="search-box" id="search-box" placeholder="Search test name..." onkeyup="filterByName()">
        </div>
        
        <div id="table-container">
            <table id="execution-table">
                <thead>
                    <tr>
                        <th style="width: 60px;">Order</th>
                        <th>Test Name</th>
                        <th style="width: 100px;">Status</th>
                        <th style="width: 100px;">Duration (s)</th>
                    </tr>
                </thead>
                <tbody id="test-body">
                </tbody>
            </table>
        </div>
        
        <div class="note">
            <strong>📌 About This Report:</strong>
            This report displays tests in their exact execution order as defined by the group file (<code>{grp_name}</code>).
            Unlike pytest-html which groups by outcome, this report preserves the original test sequence.
            Use this for understanding test dependencies and execution flow.
        </div>
        
        <div class="footer">
            Generated by DSL Test Suite | Execution Order Report v2 | pytest-html integration
        </div>
    </div>
    
    <script>
        // Load execution order and test results data
        const orderMap = JSON.parse('PLACEHOLDER_ORDER');
        const resultsMap = JSON.parse('PLACEHOLDER_RESULTS');
        
        let allTests = [];
        let currentFilter = 'ALL';
        
        // Populate table with test data
        function populateTable() {{
            const tbody = document.getElementById('test-body');
            tbody.innerHTML = '';
            
            let totalTests = 0;
            let passedTests = 0;
            let failedTests = 0;
            let skippedTests = 0;
            
            // Get tests from order
            allTests = Object.entries(orderMap)
                .map(([name, order]) => {{
                    const result = resultsMap[name] || {{'outcome': 'UNKNOWN', 'duration': 0}};
                    
                    totalTests++;
                    if (result.outcome === 'PASSED') passedTests++;
                    else if (result.outcome === 'FAILED') failedTests++;
                    else if (result.outcome === 'SKIPPED') skippedTests++;
                    
                    return {{
                        order: order,
                        name: name,
                        status: result.outcome || 'UNKNOWN',
                        duration: result.duration || 0
                    }};
                }})
                .sort((a, b) => a.order - b.order);
            
            // Populate table
            displayTests(allTests);
            
            // Update summary
            document.getElementById('sum-total').textContent = totalTests;
            document.getElementById('sum-passed').textContent = passedTests;
            document.getElementById('sum-failed').textContent = failedTests;
            document.getElementById('sum-skipped').textContent = skippedTests;
        }}
        
        function displayTests(tests) {{
            const tbody = document.getElementById('test-body');
            tbody.innerHTML = '';
            
            if (tests.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="4" class="no-data">No tests to display</td></tr>';
                return;
            }}
            
            tests.forEach((test, index) => {{
                const row = tbody.insertRow();
                
                const orderCell = row.insertCell(0);
                orderCell.innerHTML = '<div class="order">' + (test.order + 1) + '</div>';
                
                const nameCell = row.insertCell(1);
                nameCell.className = 'test-name';
                nameCell.textContent = test.name;
                
                const statusCell = row.insertCell(2);
                statusCell.className = 'status ' + test.status;
                statusCell.textContent = test.status;
                
                const durationCell = row.insertCell(3);
                durationCell.className = 'duration';
                durationCell.textContent = test.duration.toFixed(2) + 's';
                
                row.dataset.status = test.status;
                row.dataset.name = test.name.toLowerCase();
            }});
        }}
        
        function filterTests(status) {{
            currentFilter = status;
            
            // Update button states
            document.querySelectorAll('.control-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
            
            // Filter table
            const tbody = document.getElementById('test-body');
            const rows = tbody.querySelectorAll('tr');
            
            rows.forEach(row => {{
                if (status === 'ALL' || row.dataset.status === status) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
        
        function filterByName() {{
            const searchTerm = document.getElementById('search-box').value.toLowerCase();
            const tbody = document.getElementById('test-body');
            const rows = tbody.querySelectorAll('tr');
            
            rows.forEach(row => {{
                const name = row.dataset.name || '';
                const status = row.dataset.status || '';
                
                const nameMatch = name.includes(searchTerm);
                const statusMatch = currentFilter === 'ALL' || status === currentFilter;
                
                if (nameMatch && statusMatch) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
        
        // Initialize on load
        window.addEventListener('DOMContentLoaded', populateTable);
    </script>
</body>
</html>
"""
    
    # Replace placeholders with actual JSON data
    html_content = html_content.replace('PLACEHOLDER_ORDER', grp_order_json)
    html_content = html_content.replace('PLACEHOLDER_RESULTS', test_results_json)
    
    # Write HTML file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✓ Execution order HTML report v2 generated: {output_file}")
    
    # Print summary
    total = len(grp_order)
    passed = len([v for v in test_results.values() if v.get('outcome') == 'PASSED'])
    failed = len([v for v in test_results.values() if v.get('outcome') == 'FAILED'])
    
    print(f"  Total tests: {total}")
    print(f"  With results: {len(test_results)}")
    if test_results:
        print(f"  Passed: {passed}, Failed: {failed}")


if __name__ == "__main__":
    # Look for .pytest-order.txt in current directory
    order_file = Path(".pytest-order.txt")
    
    if not order_file.exists():
        print(f"Error: {order_file} not found")
        print("Run transpiler first: python ../run_transpiler.py -g path/to/grp.file")
        exit(1)
    
    generate_execution_html(
        order_file=order_file,
        output_file="reports/execution_order.html"
    )
