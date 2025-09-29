#!/bin/bash

# Docker Test Runner Script for Chat Platform
# This script runs tests in a Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
CLEANUP=true
BUILD=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --no-build)
            BUILD=false
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Show help
show_help() {
    echo "Docker Test Runner for Chat Platform"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: all, unit, integration, e2e (default: all)"
    echo "  -c, --coverage         Run with coverage report"
    echo "  -v, --verbose          Verbose output"
    echo "  --no-cleanup           Don't cleanup containers after tests"
    echo "  --no-build             Don't rebuild Docker image"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests"
    echo "  $0 -t unit -c                        # Run unit tests with coverage"
    echo "  $0 -t integration -v                 # Run integration tests verbosely"
    echo "  $0 --no-cleanup                      # Keep containers after tests"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker..."
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is running"
}

# Build test Docker image
build_test_image() {
    if [ "$BUILD" = true ]; then
        print_status "Building test Docker image..."
        
        docker build -f Dockerfile.test -t chat-platform-test .
        
        print_success "Test image built successfully"
    else
        print_status "Skipping image build"
    fi
}

# Run tests in Docker container
run_tests_in_docker() {
    print_status "Running tests in Docker container..."
    
    # Build pytest command
    local pytest_cmd="pytest tests/"
    
    # Add test type markers
    case $TEST_TYPE in
        "unit")
            pytest_cmd="$pytest_cmd -m \"not integration and not e2e\""
            ;;
        "integration")
            pytest_cmd="$pytest_cmd -m \"integration\""
            ;;
        "e2e")
            pytest_cmd="$pytest_cmd -m \"e2e\""
            ;;
        "all")
            # No additional markers
            ;;
        *)
            print_error "Invalid test type: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # Add verbosity
    if [ "$VERBOSE" = true ]; then
        pytest_cmd="$pytest_cmd -v -s"
    fi
    
    # Add coverage
    if [ "$COVERAGE" = true ]; then
        pytest_cmd="$pytest_cmd --cov=app --cov-report=html --cov-report=term-missing"
    fi
    
    # Add additional options
    pytest_cmd="$pytest_cmd --strict-markers --disable-warnings --color=yes"
    
    # Run tests in container
    docker run --rm \
        -v $(pwd)/tests:/app/tests \
        -v $(pwd)/app:/app/app \
        -v $(pwd)/htmlcov:/app/htmlcov \
        -e TESTING=true \
        -e DATABASE_URL="sqlite:///./test_chat.db" \
        -e CACHE_ENABLED=false \
        chat-platform-test \
        bash -c "$pytest_cmd"
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "All tests passed!"
        
        if [ "$COVERAGE" = true ]; then
            print_status "Coverage report generated in htmlcov/index.html"
        fi
    else
        print_error "Some tests failed!"
        return $exit_code
    fi
}

# Create Dockerfile.test
create_test_dockerfile() {
    print_status "Creating test Dockerfile..."
    
    cat > Dockerfile.test << 'EOF'
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' testuser \
    && chown -R testuser:testuser /app
USER testuser

# Default command
CMD ["pytest", "tests/", "-v"]
EOF

    print_success "Test Dockerfile created"
}

# Cleanup function
cleanup() {
    if [ "$CLEANUP" = true ]; then
        print_status "Cleaning up..."
        
        # Remove test containers
        docker ps -a --filter "ancestor=chat-platform-test" --format "{{.ID}}" | xargs -r docker rm -f
        
        # Remove test image
        docker rmi chat-platform-test 2>/dev/null || true
        
        print_success "Cleanup completed"
    else
        print_status "Skipping cleanup"
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "🐳 Chat Platform Docker Test Runner"
    echo "=========================================="
    
    # Set trap for cleanup on exit
    trap cleanup EXIT
    
    check_docker
    create_test_dockerfile
    build_test_image
    run_tests_in_docker
}

# Run main function
main "$@"
