#!/bin/bash

# Configuration Validation Script for Crypto Trading MCP System
# Quick wrapper around the Python validation script

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔍 Crypto Trading MCP System - Configuration Validator"
echo "================================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not installed"
    exit 1
fi

# Check if required Python modules are available
python3 -c "import yaml" 2>/dev/null || {
    echo "⚠️  Warning: PyYAML not found. Installing..."
    pip3 install PyYAML || {
        echo "❌ Error: Failed to install PyYAML. Please install manually: pip3 install PyYAML"
        exit 1
    }
}

# Run the validation
python3 "${PROJECT_ROOT}/scripts/validate-config.py"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "🎉 Configuration validation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Copy .env.example to .env and configure your API keys"
    echo "2. Review any warnings and address them if needed"
    echo "3. Run 'docker-compose up -d' to start the system"
else
    echo ""
    echo "💥 Configuration validation failed!"
    echo ""
    echo "Please fix the critical issues listed above before proceeding."
fi

exit $exit_code