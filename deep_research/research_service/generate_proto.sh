#!/bin/bash
# Generate Python protobuf files from .proto definition

cd "$(dirname "$0")"

python -m grpc_tools.protoc \
    -I proto \
    --python_out=proto \
    --grpc_python_out=proto \
    proto/research_service.proto

# Fix import in generated grpc file
sed -i '' 's/import research_service_pb2 as research__service__pb2/from . import research_service_pb2 as research__service__pb2/' proto/research_service_pb2_grpc.py


echo "Protobuf files generated successfully!"

