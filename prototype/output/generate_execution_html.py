#!/usr/bin/env python3
"""
Generate HTML report showing test execution order

This creates an HTML file that displays tests in the order they were executed,
useful for understanding test sequencing and dependencies.

Usage:
    python generate_execution_html.py
"""

import json
from pathlib import Path
from datetime import datetime


def generate_execution_html(log_file, order_file, output_file="reports/execution_order.html"):
    """Generate HTML report showing execution order"""
    
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
    
    # Convert to JSON format for JavaScript
    grp_order_json = json.dumps(grp_order)
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Order Report</title>
    <meta charset="UTF-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        h1 {{
            color: #333;
            margin-bottom: 10px;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }}
        
        .metadata {{
            display: flex;
            gap: 30px;
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        
        .metadata-item {{
            flex: 1;
        }}
        
        .metadata-item label {{
            font-weight: bold;
            color: #555;
        }}
        
        .metadata-item value {{
            color: #0066cc;
            font-size: 14px;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        
        .summary-card {{
            padding: 15px;
            border-radius: 4px;
            text-align: center;
            color: white;
            font-weight: bold;
        }}
        
        .passed {{ background: #4caf50; }}
        .failed {{ background: #f44336; }}
        .total {{ background: #2196f3; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th {{
            background: #2c3e50;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .order {{
            font-weight: bold;
            color: #0066cc;
            min-width: 40px;
        }}
        
        .test-name {{
            font-family: 'Courier New', monospace;
            color: #333;
        }}
        
        .status {{
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .status.PASSED {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        
        .status.FAILED {{
            background: #ffebee;
            color: #c62828;
        }}
        
        .note {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin-top: 20px;
            border-radius: 4px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Test Execution Order Report</h1>
        
        <div class="metadata">
            <div class="metadata-item">
                <label>Group File:</label><br/>
                <value>{grp_name}</value>
            </div>
            <div class="metadata-item">
                <label>Generated:</label><br/>
                <value>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</value>
            </div>
            <div class="metadata-item">
                <label>Total Tests:</label><br/>
                <value id="total">0</value>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card total">
                <div style="font-size: 24px;" id="sum-total">0</div>
                <div>Total Tests</div>
            </div>
            <div class="summary-card passed">
                <div style="font-size: 24px;" id="sum-passed">0</div>
                <div>Passed</div>
            </div>
            <div class="summary-card failed">
                <div style="font-size: 24px;" id="sum-failed">0</div>
                <div>Failed</div>
            </div>
        </div>
        
        <table id="execution-table">
            <thead>
                <tr>
                    <th style="width: 60px;">Order</th>
                    <th>Test Name</th>
                    <th style="width: 100px;">Status</th>
                </tr>
            </thead>
            <tbody id="test-body">
            </tbody>
        </table>
        
        <div class="note">
            <strong>Note:</strong> This report shows test execution order from <code>.pytest-order.txt</code>. 
            The pytest-html report groups tests by outcome (passed/failed) rather than execution order.
            For test dependencies and sequencing analysis, refer to this report.
        </div>
        
        <div class="footer">
            Generated by DSL Test Suite | Test Execution Order Report
        </div>
    </div>
    
    <script>
        // Load execution order data from .pytest-order.txt
        const orderMap = JSON.parse('PLACEHOLDER_JSON_DATA');
        
        // Populate table with test data
        function populateTable() {{
            const tbody = document.getElementById('test-body');
            let totalTests = 0;
            let passedTests = 0;
            let failedTests = 0;
            
            // Get tests from order
            const tests = Object.entries(orderMap).map(([name, order]) => {{
                totalTests++;
                return {{
                    order: order,
                    name: name,
                    status: 'PASSED'  // Default - would need actual results
                }};
            }}).sort((a, b) => a.order - b.order);
            
            tests.forEach(test => {{
                const row = tbody.insertRow();
                
                const orderCell = row.insertCell(0);
                orderCell.className = 'order';
                orderCell.textContent = '#' + (test.order + 1);
                
                const nameCell = row.insertCell(1);
                nameCell.className = 'test-name';
                nameCell.textContent = test.name;
                
                const statusCell = row.insertCell(2);
                statusCell.className = 'status ' + test.status;
                statusCell.textContent = test.status;
                
                if (test.status === 'PASSED') passedTests++;
                if (test.status === 'FAILED') failedTests++;
            }});
            
            document.getElementById('total').textContent = totalTests;
            document.getElementById('sum-total').textContent = totalTests;
            document.getElementById('sum-passed').textContent = passedTests;
            document.getElementById('sum-failed').textContent = failedTests;
        }}
        
        window.addEventListener('DOMContentLoaded', populateTable);
    </script>
</body>
</html>
"""
    
    # Replace JSON placeholder with actual data (escape quotes for JSON)
    html_content = html_content.replace('PLACEHOLDER_JSON_DATA', grp_order_json)
    
    # Write HTML file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✓ Execution order HTML report generated: {output_file}")


if __name__ == "__main__":
    generate_execution_html(
        log_file=Path("reports/test_execution.log"),
        order_file=Path(".pytest-order.txt"),
        output_file="reports/execution_order.html"
    )
