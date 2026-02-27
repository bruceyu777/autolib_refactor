#!/bin/bash
# Quick start script for DSL test suite

set -e

echo "=================================================="
echo "  DSL Test Suite - Quick Start"
echo "=================================================="
echo ""

# Check if in correct directory
if [ ! -f "pytest.ini" ]; then
    echo "Error: Must be run from the output directory"
    echo "Usage: cd /home/fosqa/autolibv3/autolib_v3/prototype/output"
    echo "       ./quickstart.sh"
    exit 1
fi

# Check dependencies
echo "Checking dependencies..."
python3 -c "import pytest" 2>/dev/null || {
    echo "Installing pytest..."
    pip install pytest pytest-html pytest-cov pytest-mock
}

# Create reports directory
mkdir -p reports

echo ""
echo "✓ Dependencies installed"
echo ""

# Show available tests
echo "Available tests:"
find testcases -name "test_*.py" | sed 's|testcases/||' | sort | nl
echo ""

# Show quick commands
echo "Quick commands:"
echo "  make test              # Run all tests"
echo "  make test QAID=205812  # Run specific test"
echo "  make test-verbose      # Run with verbose output"
echo "  make report            # Open HTML report"
echo "  make help              # Show all commands"
echo ""

# Offer to run tests
read -p "Run all tests now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    make test-all
    echo ""
    echo "✓ Tests complete!"
    echo ""
    echo "View reports:"
    echo "  HTML: reports/test_report.html"
    echo "  XML:  reports/test_report.xml" 
    echo "  Log:  reports/test_execution.log"
    echo ""
else
    echo ""
    echo "To run tests manually, use:"
    echo "  make test"
    echo ""
fi

echo "=================================================="
