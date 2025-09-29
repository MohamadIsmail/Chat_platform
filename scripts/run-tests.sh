#!/bin/bash

# Test Runner Script for Chat Platform
# This script provides various options for running tests

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
PARALLEL=false
MARKERS=""
OUTPUT_FORMAT="short"

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
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
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
    echo "Test Runner for Chat Platform"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: all, unit, integration, e2e (default: all)"
    echo "  -c, --coverage         Run with coverage report"
    echo "  -v, --verbose          Verbose output"
    echo "  -p, --parallel         Run tests in parallel"
    echo "  -m, --markers MARKERS  Run tests with specific markers"
    echo "  -f, --format FORMAT    Output format: short, long, line (default: short)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests"
    echo "  $0 -t unit -c                        # Run unit tests with coverage"
    echo "  $0 -m auth -v                        # Run authentication tests verbosely"
    echo "  $0 -t integration -p                 # Run integration tests in parallel"
    echo "  $0 -m 'not slow' -c                  # Run non-slow tests with coverage"
}

# Check if pytest is installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v pytest &> /dev/null; then
        print_error "pytest is not installed. Please install test dependencies:"
        echo "pip install -r requirements.txt"
        exit 1
    fi
    
    if [ "$COVERAGE" = true ] && ! command -v coverage &> /dev/null; then
        print_warning "coverage is not installed. Installing..."
        pip install coverage
    fi
    
    print_success "Dependencies checked"
}

# Setup test environment
setup_environment() {
    print_status "Setting up test environment..."
    
    # Set environment variables for testing
    export TESTING=true
    export DATABASE_URL="sqlite:///./test_chat.db"
    export REDIS_URL="redis://localhost:6379/1"  # Use different Redis DB for testing
    export CACHE_ENABLED=false  # Disable cache for testing
    
    # Create test database directory
    mkdir -p tests/data
    
    print_success "Test environment setup completed"
}

# Build pytest command
build_pytest_command() {
    local cmd="pytest"
    
    # Add test path
    cmd="$cmd tests/"
    
    # Add markers if specified
    if [ -n "$MARKERS" ]; then
        cmd="$cmd -m \"$MARKERS\""
    fi
    
    # Add test type markers
    case $TEST_TYPE in
        "unit")
            cmd="$cmd -m \"not integration and not e2e\""
            ;;
        "integration")
            cmd="$cmd -m \"integration\""
            ;;
        "e2e")
            cmd="$cmd -m \"e2e\""
            ;;
        "auth")
            cmd="$cmd -m \"auth\""
            ;;
        "messages")
            cmd="$cmd -m \"messages\""
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
        cmd="$cmd -v -s"
    fi
    
    # Add output format
    case $OUTPUT_FORMAT in
        "short")
            cmd="$cmd --tb=short"
            ;;
        "long")
            cmd="$cmd --tb=long"
            ;;
        "line")
            cmd="$cmd --tb=line"
            ;;
        *)
            print_error "Invalid output format: $OUTPUT_FORMAT"
            exit 1
            ;;
    esac
    
    # Add parallel execution
    if [ "$PARALLEL" = true ]; then
        if command -v pytest-xdist &> /dev/null; then
            cmd="$cmd -n auto"
        else
            print_warning "pytest-xdist not installed. Running tests sequentially."
        fi
    fi
    
    # Add coverage
    if [ "$COVERAGE" = true ]; then
        cmd="$cmd --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml"
    fi
    
    # Add additional options
    cmd="$cmd --strict-markers --disable-warnings --color=yes"
    
    echo "$cmd"
}

# Run tests
run_tests() {
    local pytest_cmd=$(build_pytest_command)
    
    print_status "Running tests..."
    print_status "Command: $pytest_cmd"
    echo ""
    
    # Execute the command
    eval $pytest_cmd
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "All tests passed!"
        
        if [ "$COVERAGE" = true ]; then
            print_status "Coverage report generated in htmlcov/index.html"
        fi
    else
        print_error "Some tests failed!"
        exit $exit_code
    fi
}

# Cleanup test environment
cleanup_environment() {
    print_status "Cleaning up test environment..."
    
    # Remove test database
    if [ -f "test_chat.db" ]; then
        rm -f test_chat.db
    fi
    
    # Remove test data directory
    if [ -d "tests/data" ]; then
        rm -rf tests/data
    fi
    
    # Remove coverage files if not keeping them
    if [ "$COVERAGE" = false ]; then
        rm -rf htmlcov/
        rm -f .coverage
        rm -f coverage.xml
    fi
    
    print_success "Cleanup completed"
}

# Run specific test suites
run_unit_tests() {
    print_status "Running unit tests..."
    pytest tests/ -m "not integration and not e2e" -v
}

run_integration_tests() {
    print_status "Running integration tests..."
    pytest tests/ -m "integration" -v
}

run_auth_tests() {
    print_status "Running authentication tests..."
    pytest tests/test_auth.py -v
}

run_message_tests() {
    print_status "Running message tests..."
    pytest tests/test_messages.py -v
}

# Main execution
main() {
    echo "=========================================="
    echo "🧪 Chat Platform Test Runner"
    echo "=========================================="
    
    check_dependencies
    setup_environment
    
    # Set trap for cleanup on exit
    trap cleanup_environment EXIT
    
    run_tests
}

# Run main function
main "$@"
