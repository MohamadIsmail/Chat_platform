#!/bin/bash

# Docker Setup Script for Chat Platform
# This script sets up the entire chat platform with Docker

set -e

echo "🚀 Setting up Chat Platform with Docker..."

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

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p docker/postgres
    mkdir -p docker/redis
    mkdir -p docker/nginx/ssl
    mkdir -p scripts
    mkdir -p logs
    
    print_success "Directories created"
}

# Generate SSL certificates for development
generate_ssl_certificates() {
    print_status "Generating SSL certificates for development..."
    
    if [ ! -f "docker/nginx/ssl/cert.pem" ] || [ ! -f "docker/nginx/ssl/key.pem" ]; then
        openssl req -x509 -newkey rsa:4096 -keyout docker/nginx/ssl/key.pem -out docker/nginx/ssl/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        print_success "SSL certificates generated"
    else
        print_warning "SSL certificates already exist, skipping generation"
    fi
}

# Create .env file if it doesn't exist
create_env_file() {
    print_status "Setting up environment file..."
    
    if [ ! -f ".env" ]; then
        cp docker.env .env
        print_success "Environment file created from docker.env"
        print_warning "Please review and update .env file with your specific settings"
    else
        print_warning ".env file already exists, skipping creation"
    fi
}

# Build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Build the application image
    docker-compose build app
    
    # Start core services (postgres, redis, app)
    docker-compose up -d postgres redis app
    
    print_success "Core services started"
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 10
    
    # Check service health
    if docker-compose ps | grep -q "Up (healthy)"; then
        print_success "Services are healthy and ready"
    else
        print_warning "Some services may not be fully ready yet"
    fi
}

# Start development services
start_dev_services() {
    print_status "Starting development services (PgAdmin, Redis Commander)..."
    
    docker-compose --profile development up -d pgadmin redis-commander
    
    print_success "Development services started"
    print_status "PgAdmin: http://localhost:5050 (admin@chatplatform.com / admin_password)"
    print_status "Redis Commander: http://localhost:8081"
}

# Start production services
start_prod_services() {
    print_status "Starting production services (Nginx)..."
    
    docker-compose --profile production up -d nginx
    
    print_success "Production services started"
    print_status "Application: http://localhost (HTTP) or https://localhost (HTTPS)"
}

# Show service status
show_status() {
    print_status "Service Status:"
    docker-compose ps
    
    echo ""
    print_status "Service URLs:"
    echo "  🌐 Application: http://localhost:8000"
    echo "  📊 API Docs: http://localhost:8000/docs"
    echo "  ❤️  Health Check: http://localhost:8000/health"
    echo "  📈 Cache Stats: http://localhost:8000/cache/stats"
    
    if docker-compose ps | grep -q "pgadmin"; then
        echo "  🗄️  PgAdmin: http://localhost:5050"
    fi
    
    if docker-compose ps | grep -q "redis-commander"; then
        echo "  🔴 Redis Commander: http://localhost:8081"
    fi
    
    if docker-compose ps | grep -q "nginx"; then
        echo "  🌍 Nginx (Production): http://localhost"
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "🐳 Chat Platform Docker Setup"
    echo "=========================================="
    
    check_docker
    create_directories
    generate_ssl_certificates
    create_env_file
    
    # Parse command line arguments
    case "${1:-dev}" in
        "dev")
            start_services
            start_dev_services
            ;;
        "prod")
            start_services
            start_prod_services
            ;;
        "core")
            start_services
            ;;
        *)
            print_error "Invalid option: $1"
            echo "Usage: $0 [dev|prod|core]"
            echo "  dev  - Start all services including development tools (default)"
            echo "  prod - Start production services with Nginx"
            echo "  core - Start only core services (app, postgres, redis)"
            exit 1
            ;;
    esac
    
    show_status
    
    echo ""
    print_success "Chat Platform setup completed!"
    print_status "Run 'docker-compose logs -f app' to see application logs"
    print_status "Run 'docker-compose down' to stop all services"
}

# Run main function
main "$@"
