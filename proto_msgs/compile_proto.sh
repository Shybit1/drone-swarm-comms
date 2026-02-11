#!/bin/bash

##############################################################################
# compile_proto.sh
#
# Compiles all Protocol Buffer definitions in proto_msgs/ to Python code.
# Should be run before simulation launch or as part of setup.py.
#
# Usage:
#   ./proto_msgs/compile_proto.sh
#
##############################################################################

set -e

PROTO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$PROTO_DIR"

echo "[PROTO] Compiling Protocol Buffer definitions..."
echo "[PROTO] Source directory: $PROTO_DIR"
echo "[PROTO] Output directory: $OUTPUT_DIR"

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "[ERROR] protoc compiler not found. Install: apt-get install protobuf-compiler"
    exit 1
fi

# Compile all .proto files in the directory
cd "$PROTO_DIR"
protoc \
    --python_out="$OUTPUT_DIR" \
    --pyi_out="$OUTPUT_DIR" \
    *.proto

if [ $? -eq 0 ]; then
    echo "[PROTO] Compilation successful!"
    echo "[PROTO] Generated Python files:"
    ls -1 *_pb2.py *_pb2.pyi 2>/dev/null || echo "  (no files found - check compiler output above)"
else
    echo "[ERROR] Protocol buffer compilation failed"
    exit 1
fi

# Create __init__.py if it doesn't exist (to make proto_msgs a package)
if [ ! -f "$OUTPUT_DIR/__init__.py" ]; then
    touch "$OUTPUT_DIR/__init__.py"
    echo "[PROTO] Created __init__.py"
fi

echo "[PROTO] Done!"
