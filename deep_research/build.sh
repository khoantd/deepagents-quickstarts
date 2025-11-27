#!/bin/bash
# Docker image build script for Deep Research Application
# Provides convenient options for building, tagging, and pushing images

set -e

# Default values
IMAGE_NAME="deep-research"
IMAGE_TAG="latest"
SERVICE_MODE="langgraph"
PUSH_IMAGE=false
REGISTRY=""
PLATFORM=""
BUILD_ARGS=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Print usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build Docker image for Deep Research Application

OPTIONS:
    -t, --tag TAG           Image tag (default: latest)
    -n, --name NAME         Image name (default: deep-research)
    -m, --mode MODE         Service mode: langgraph, fastapi, or both (default: langgraph)
    -r, --registry REG      Docker registry (e.g., docker.io/username or ghcr.io/username)
    -P, --platform PLATFORM Target platform (e.g., linux/amd64, linux/arm64, linux/arm/v7)
    -p, --push              Push image to registry after building
    -a, --arg KEY=VALUE     Build argument (can be used multiple times)
    -h, --help              Show this help message

EXAMPLES:
    # Build with default settings
    $0

    # Build with custom tag
    $0 -t v1.0.0

    # Build and push to Docker Hub
    $0 -r docker.io/username -p

    # Build for specific platform (ARM64)
    $0 -P linux/arm64 -t v1.0.0-arm64

    # Build for AMD64 platform and push to registry
    $0 -r ghcr.io/username -P linux/amd64 -p

    # Build for FastAPI service mode
    $0 -m fastapi -t fastapi-v1.0.0

    # Build with build arguments
    $0 -a PYTHON_VERSION=3.12 -a SERVICE_MODE=both

    # Build for multiple platforms (requires docker buildx)
    $0 -r docker.io/username -P linux/amd64,linux/arm64 -p

NOTES:
    - For FastAPI service mode, JWT authentication is required:
      Set JWT_SECRET_KEY and API_KEYS environment variables when running the container
    - See docs/jwt_setup.md for JWT authentication setup details
    - Protobuf files (research_service/proto/*_pb2*.py) must be generated before building
      Run: cd research_service && ./generate_proto.sh

EOF
}

# Check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    print_success "Docker is available"
}

# Validate required files exist
validate_files() {
    local missing_files=()
    
    if [ ! -f "Dockerfile" ]; then
        missing_files+=("Dockerfile")
    fi
    
    if [ ! -f "pyproject.toml" ]; then
        missing_files+=("pyproject.toml")
    fi
    
    if [ ! -f "docker-entrypoint.sh" ]; then
        missing_files+=("docker-entrypoint.sh")
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_error "Missing required files: ${missing_files[*]}"
        exit 1
    fi
    
    # Check for protobuf files if building for fastapi or both modes
    if [[ "$SERVICE_MODE" == "fastapi" ]] || [[ "$SERVICE_MODE" == "both" ]]; then
        if [ ! -f "research_service/proto/research_service_pb2.py" ] || \
           [ ! -f "research_service/proto/research_service_pb2_grpc.py" ]; then
            print_warning "Protobuf files not found. They should be generated before building."
            print_info "Run: cd research_service && ./generate_proto.sh"
            print_info "Continuing build anyway (protobuf files may be generated during build)..."
        fi
    fi
    
    print_success "Required files found"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -n|--name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -m|--mode)
                SERVICE_MODE="$2"
                if [[ ! "$SERVICE_MODE" =~ ^(langgraph|fastapi|both)$ ]]; then
                    print_error "Invalid service mode: $SERVICE_MODE"
                    echo "Valid modes: langgraph, fastapi, both"
                    exit 1
                fi
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -P|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            -p|--push)
                PUSH_IMAGE=true
                shift
                ;;
            -a|--arg)
                BUILD_ARGS="$BUILD_ARGS --build-arg $2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Build Docker image
build_image() {
    local full_image_name
    
    if [ -n "$REGISTRY" ]; then
        full_image_name="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    else
        full_image_name="${IMAGE_NAME}:${IMAGE_TAG}"
    fi
    
    print_info "Building Docker image: ${full_image_name}"
    print_info "Service mode: ${SERVICE_MODE}"
    if [ -n "$PLATFORM" ]; then
        print_info "Platform: ${PLATFORM}"
    fi
    echo ""
    
    # Check if buildx is needed for multi-platform builds
    local use_buildx=false
    if [ -n "$PLATFORM" ] && [[ "$PLATFORM" == *","* ]]; then
        use_buildx=true
        if ! docker buildx version &> /dev/null; then
            print_error "Multi-platform builds require docker buildx, but it's not available"
            print_info "Install buildx or use a single platform"
            exit 1
        fi
        print_info "Using docker buildx for multi-platform build"
    fi
    
    # Build command
    local build_cmd=""
    if [ "$use_buildx" = true ]; then
        # Use buildx for multi-platform builds
        build_cmd="docker buildx build \
            --platform ${PLATFORM} \
            --build-arg SERVICE_MODE=${SERVICE_MODE} \
            ${BUILD_ARGS} \
            -t ${full_image_name}"
        
        # Add --push if pushing and using buildx
        if [ "$PUSH_IMAGE" = true ]; then
            build_cmd="${build_cmd} --push"
        else
            build_cmd="${build_cmd} --load"
        fi
        
        build_cmd="${build_cmd} ."
    else
        # Standard docker build
        build_cmd="docker build \
            --build-arg SERVICE_MODE=${SERVICE_MODE} \
            ${BUILD_ARGS}"
        
        # Add platform flag if specified
        if [ -n "$PLATFORM" ]; then
            build_cmd="${build_cmd} --platform ${PLATFORM}"
        fi
        
        build_cmd="${build_cmd} -t ${full_image_name} ."
    fi
    
    if eval "$build_cmd"; then
        print_success "Image built successfully: ${full_image_name}"
        
        # Show image size (only for single platform builds or when not using buildx with --push)
        if [ "$use_buildx" = false ] || [ "$PUSH_IMAGE" = false ]; then
            local image_size=$(docker images "${full_image_name}" --format "{{.Size}}" 2>/dev/null || echo "N/A")
            if [ "$image_size" != "N/A" ]; then
                print_info "Image size: ${image_size}"
            fi
        fi
        
        return 0
    else
        print_error "Failed to build image"
        return 1
    fi
}

# Push Docker image
push_image() {
    # If using buildx with --push, image was already pushed during build
    if [ -n "$PLATFORM" ] && [[ "$PLATFORM" == *","* ]] && [ "$PUSH_IMAGE" = true ]; then
        print_info "Image was pushed during multi-platform build"
        return 0
    fi
    
    if [ "$PUSH_IMAGE" = false ]; then
        return 0
    fi
    
    if [ -z "$REGISTRY" ]; then
        print_warning "No registry specified. Skipping push."
        print_info "Use -r/--registry to specify a registry"
        return 0
    fi
    
    local full_image_name="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    
    print_info "Pushing image to registry: ${full_image_name}"
    
    if docker push "${full_image_name}"; then
        print_success "Image pushed successfully: ${full_image_name}"
    else
        print_error "Failed to push image"
        return 1
    fi
}

# Main execution
main() {
    echo "🐳 Docker Image Builder for Deep Research"
    echo "=========================================="
    echo ""
    
    parse_args "$@"
    
    check_docker
    validate_files
    
    echo ""
    
    if build_image; then
        push_image
        echo ""
        print_success "Build process completed!"
        echo ""
        print_info "To run the image:"
        echo ""
        
        # Determine image name
        local image_name
        if [ -n "$REGISTRY" ]; then
            image_name="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        else
            image_name="${IMAGE_NAME}:${IMAGE_TAG}"
        fi
        
        # Build example docker run command
        echo "  docker run \\"
        
        # Add port mappings based on service mode
        if [[ "$SERVICE_MODE" == "langgraph" ]] || [[ "$SERVICE_MODE" == "both" ]]; then
            echo "    -p 8123:8123 \\"
        fi
        if [[ "$SERVICE_MODE" == "fastapi" ]] || [[ "$SERVICE_MODE" == "both" ]]; then
            echo "    -p 8081:8081 -p 50052:50052 \\"
        fi
        
        # Add service mode
        echo "    -e SERVICE_MODE=${SERVICE_MODE} \\"
        
        # Add required environment variables for FastAPI mode
        if [[ "$SERVICE_MODE" == "fastapi" ]] || [[ "$SERVICE_MODE" == "both" ]]; then
            echo "    -e JWT_SECRET_KEY=your-secret-key \\"
            echo "    -e API_KEYS=api-key-1,api-key-2 \\"
        fi
        
        # Add common API keys
        echo "    -e ANTHROPIC_API_KEY=your-key \\"
        echo "    -e TAVILY_API_KEY=your-key \\"
        echo "    ${image_name}"
        
        echo ""
        if [[ "$SERVICE_MODE" == "fastapi" ]] || [[ "$SERVICE_MODE" == "both" ]]; then
            print_warning "Note: FastAPI service requires JWT_SECRET_KEY and API_KEYS environment variables"
            print_info "See docs/jwt_setup.md for JWT authentication setup details"
        fi
    else
        print_error "Build failed"
        exit 1
    fi
}

# Run main function
main "$@"

