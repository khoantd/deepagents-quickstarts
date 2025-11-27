# Build for ARM64 platform
./build.sh -P linux/arm64 -t v1.0.0-arm64

# Build for AMD64 and push to registry
./build.sh -r ghcr.io/username -P linux/amd64 -p

# Multi-platform build (requires buildx)
./build.sh -r docker.io/username -P linux/amd64,linux/arm64 -p