#!/bin/bash
# Docker entrypoint script for AI Paper Reader

set -e

echo "=============================================="
echo "AI Paper Reader - Container Starting"
echo "=============================================="

# Create necessary directories
mkdir -p /app/data/scans
mkdir -p /app/data/logs
mkdir -p /app/data/output

# Set permissions
chmod -R 755 /app/data

echo "✅ Directories initialized"
echo "✅ Container ready"
echo ""
echo "Available CLI tools:"
echo "  - python intake_cli.py"
echo "  - python prep_cli.py"
echo "  - python scan_cli.py"
echo ""
echo "=============================================="

# Execute the main command
exec "$@"
